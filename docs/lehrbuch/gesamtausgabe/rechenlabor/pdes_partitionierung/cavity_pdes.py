"""Linux multiprocess CP2/2 experiment. Uses the published QSS and cavity kernels."""
import argparse
import functools
import hashlib
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import queue
import random
import struct
import sys
import time
import traceback

import numpy as np

from buchquellen import CAVITY_BASIS, read_book_source, solver_root


LAYOUTS = ('rows', 'columns', 'tiles', 'cyclic')
MODES = ('conservative', 'optimistic')


def validate_layout(count, layout):
    if count < 1:
        raise ValueError('Rank count must be positive')
    if layout not in LAYOUTS:
        raise ValueError(f'Unknown layout: {layout}')
    if layout == 'tiles' and count > 1 and count % 2:
        raise ValueError('The tiles layout requires 1 or an even number of ranks')


def partitions(side, count, layout):
    validate_layout(count, layout)
    grid = np.arange(side * side).reshape(side, side)
    if layout == 'rows':
        ny, nx = count, 1
    elif layout == 'columns':
        ny, nx = 1, count
    elif layout == 'tiles':
        ny, nx = (2, count // 2) if count > 1 else (1, 1)
    elif layout == 'cyclic':
        return [np.arange(r, grid.size, count) for r in range(count)]
    else:
        raise ValueError(layout)
    return [tile.ravel() for slab in np.array_split(grid, ny, axis=0)
            for tile in np.array_split(slab, nx, axis=1)]


class Star:
    """Rank zero performs the global Poisson solve and global scalar reductions."""
    def __init__(self, rank, channel, ids):
        self.rank, self.channel, self.ids = rank, channel, ids
        self.bytes_sent = {}
        self.messages = {}

    def send(self, pipe, kind, data):
        self.bytes_sent[kind] = self.bytes_sent.get(kind, 0) + len(data)
        self.messages[kind] = self.messages.get(kind, 0) + 1
        pipe.send_bytes(data)

    def reduce(self, value, operator, kind):
        if len(self.ids) == 1:
            return value
        if self.rank:
            self.send(self.channel, kind, struct.pack('=d', value))
            return struct.unpack('=d', self.channel.recv_bytes())[0]
        values = [value, *(struct.unpack('=d', c.recv_bytes())[0] for c in self.channel)]
        result = operator(values)
        for pipe in self.channel:
            self.send(pipe, kind, struct.pack('=d', result))
        return result

    def rhs(self, cavity, t, local):
        array = np.asarray(local, dtype='=f8')
        if len(self.ids) == 1:
            return cavity.rhs(t, array)
        if self.rank:
            self.send(self.channel, 'poisson_fields', array.tobytes())
            return np.frombuffer(self.channel.recv_bytes(), dtype='=f8')
        state = np.empty(cavity.dim)
        state[self.ids[0]] = array
        for nodes, pipe in zip(self.ids[1:], self.channel):
            state[nodes] = np.frombuffer(pipe.recv_bytes(), dtype='=f8')
        result = cavity.rhs(t, state)
        for nodes, pipe in zip(self.ids[1:], self.channel):
            self.send(pipe, 'poisson_fields', result[nodes].tobytes())
        return result[self.ids[0]]


def distributed(rank, cpus, ids, pipe, mode, order, segments, window, epoch, results):
    try:
        os.sched_setaffinity(0, {cpus[rank]})
        star = Star(rank, pipe, ids)
        nlocal = len(ids[rank])
        cavity = Cavity(257, 1000) if rank == 0 else None
        model = IVP(functools.partial(star.rhs, cavity), 0, (0.0,) * nlocal,
                    350000 * 0.1 / 256, autonomous=True)
        def derivative_step(q, degree):
            scale = star.reduce(max(1., max(abs(v[0]) for v in q)), max, 'stencil_bounds')
            length = 1.0
            for poly in q:
                for power, coefficient in enumerate(poly[1:], 1):
                    if coefficient:
                        length = min(length, (scale / abs(coefficient)) ** (1.0 / power))
            length = star.reduce(length, min, 'stencil_bounds')
            return sys.float_info.epsilon ** (1.0 / (2 * degree - 1)) * length
        advanced._automatic_derivative_step = derivative_step
        epoch.wait(timeout=90)
        start = time.perf_counter()
        q, x, rhs_calls = advanced._bootstrap_explicit_polynomials(
            model, 0., model.y0, order, None, symmetric_stencil=True)
        snapshots = [np.zeros(nlocal)]
        times = [0.]
        events = []
        attempts = restores = revoked = 0
        for segment in range(segments):
            now = times[-1]
            root_tol = 1e-12 * max(1., abs(now))
            crossings = [advanced._boundary_time(a, b, 0.001, model.t_bound-now, root_tol)
                         for a, b in zip(x, q)]
            local = min(crossings)
            # A tentative local event actually shifts x and q and changes the quantizer.
            # Outputs stay private until the global cut is validated.
            checkpoint = None
            if mode == 'optimistic' and local <= window:
                attempts += 1
                checkpoint = x, q
                x = [advanced.shift_polynomial(poly, local) for poly in x]
                q = [advanced.shift_polynomial(poly, local) for poly in q]
                tol = 1e-12 * max(1., abs(now+local), abs(local))
                outbox = [i for i, t in enumerate(crossings) if abs(t-local) <= tol]
                for i in outbox:
                    q[i][:] = x[i][:order]
            elapsed = star.reduce(local, min, 'event_minimum')
            if not math.isfinite(elapsed) or elapsed >= model.t_bound-now:
                raise ValueError('Requested prefix extends beyond the last quantization event')
            if checkpoint is not None and local > elapsed:
                x, q = checkpoint
                restores += 1
                revoked += len(outbox)
            if checkpoint is None or local > elapsed:
                x = [advanced.shift_polynomial(poly, elapsed) for poly in x]
                q = [advanced.shift_polynomial(poly, elapsed) for poly in q]
            now += elapsed
            tol = 1e-12 * max(1., abs(now), abs(elapsed))
            due = [i for i, t in enumerate(crossings) if abs(t-elapsed) <= tol]
            events.append([int(ids[rank][i]) for i in due])
            snapshots.append(np.array([a[0] for a in x]))
            times.append(now)
            if segment+1 == segments:
                break
            for i in due:
                q[i][:] = x[i][:order]
            coefficients, used = advanced._rhs_taylor(
                model, now, q, order, None, symmetric_stencil=True)
            rhs_calls += used
            x = advanced._state_polynomials(snapshots[-1], coefficients, order)

        if rank:
            star.send(pipe, 'validation_fields', np.asarray(snapshots).tobytes())
            digest = ''
        else:
            full = np.empty((segments+1, cavity.dim), dtype='<f8')
            full[:, ids[0]] = snapshots
            for nodes, peer in zip(ids[1:], pipe):
                full[:, nodes] = np.frombuffer(peer.recv_bytes(), dtype='=f8').reshape(segments+1, -1)
            digest = hashlib.sha256(np.asarray(times,dtype='<f8').tobytes()+full.tobytes()).hexdigest()
        epoch.wait(timeout=90)
        results.put(dict(rank=rank, pid=os.getpid(), cpu=cpus[rank], kernel_s=time.perf_counter()-start,
                         sent=star.bytes_sent, messages=star.messages, digest=digest, events=events,
                         times=times, rhs=rhs_calls, attempts=attempts, restores=restores, revoked=revoked))
    except BaseException:
        results.put({'error':traceback.format_exc()})
        raise


def trial(cpus, order, count, layout, mode, segments, window):
    if mode not in MODES:
        raise ValueError(f'Unknown execution mode: {mode}')
    groups = partitions(255, count, layout)
    ctx = mp.get_context('fork')
    pipes = [ctx.Pipe() for _ in range(count-1)]
    barrier, results = ctx.Barrier(count), ctx.Queue()
    processes = [ctx.Process(target=distributed, args=(r, cpus, groups,
                 [l for l,_ in pipes] if r==0 else pipes[r-1][1],
                 mode,order,segments,window,barrier,results)) for r in range(count)]
    start=time.perf_counter()
    try:
        for p in processes: p.start()
        status=[]
        while len(status)<count:
            try: item=results.get(timeout=5)
            except queue.Empty:
                if any(p.exitcode not in (None,0) for p in processes) or time.perf_counter()-start>300:
                    raise RuntimeError('A cavity worker failed or exceeded its time limit')
                continue
            if 'error' in item: raise RuntimeError(item['error'])
            status.append(item)
        for p in processes:
            p.join(20)
            if p.exitcode!=0: raise RuntimeError('A cavity worker did not finish')
    finally:
        for p in processes:
            if p.is_alive(): p.terminate();p.join()
        for pair in pipes:
            for c in pair: c.close()
        results.close()
    wall=time.perf_counter()-start
    status.sort(key=lambda s:s['rank'])
    first=status[0]
    if not all(s['times'] == first['times'] and s['rhs'] == first['rhs'] for s in status):
        raise ValueError('Cavity ranks disagree on time stamps or RHS work')
    merged=[sorted(node for s in status for node in s['events'][j]) for j in range(segments)]
    if any(not v or len(v) != len(set(v)) for v in merged):
        raise ValueError('Missing or duplicate cavity events')
    def total_map(name):
        return {k:sum(s[name].get(k,0) for s in status) for k in sorted({k for s in status for k in s[name]})}
    return dict(order=order, ranks=count, layout=layout, mode=mode, segments=segments, window=window,
                wall_s=wall,kernel_s=max(s['kernel_s'] for s in status), rhs=first['rhs'],
                digest=first['digest'], times=first['times'], emitted=merged, payload_bytes=total_map('sent'),
                messages=total_map('messages'),rank_sizes=list(map(len,groups)),
                speculation=sum(v['attempts'] for v in status),rollbacks=sum(v['restores'] for v in status),
                revoked_quantizer_outputs=sum(v['revoked'] for v in status),cpu_ids=cpus[:count],
                distinct_processes=len({v['pid'] for v in status}))


def configure(repo):
    global Cavity, advanced, IVP, solve_ivp
    sys.path.insert(0, str(solver_root(repo)))
    from argesim_benchmarks import InitialValueProblem as IVP, solve_ivp
    from argesim_benchmarks.solvers import advanced_qss as advanced
    name = CAVITY_BASIS / 'kavitaet.py'
    source = read_book_source(repo, name)
    namespace = {'__file__': str(repo / name), '__name__': 'cavity_definition'}
    exec(compile(source, name.as_posix(), 'exec'), namespace)
    Cavity=namespace['Cavity']


def oracle(order, segments):
    cavity=Cavity(257,1000)
    times=[]
    def stop(t0,y0,t1,y1):
        times.append(t1)
        return len(times)==segments
    model=IVP(cavity.rhs,0.,(0.,)*cavity.dim,350000*.1/256,autonomous=True,_stop_after_step=stop)
    solution=solve_ivp(model,method=f'qss{order}',options={'quantum':.001,'max_events':1200000})
    return hashlib.sha256(np.asarray(solution.times,dtype='<f8').tobytes()+np.asarray(solution.states,dtype='<f8').tobytes()).hexdigest()


if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('repo', type=Path)
    a.add_argument('--order',type=int,choices=(3,4),required=True)
    a.add_argument('--segments',type=int,default=8)
    a.add_argument('--window',type=float,default=.003)
    a.add_argument('--repeats',type=int,default=3)
    a.add_argument('--layouts', nargs='+', choices=LAYOUTS, default=['rows','columns','tiles'])
    a.add_argument('--ranks',nargs='+',type=int,default=[1,4,8])
    a.add_argument('--modes', nargs='+', choices=MODES, default=MODES)
    args=a.parse_args()
    try:
        for count in args.ranks:
            for layout in args.layouts:
                validate_layout(count, layout)
    except ValueError as exc:
        a.error(str(exc))
    cpus=sorted(os.sched_getaffinity(0))
    if min(args.ranks) < 1 or max(args.ranks) > len(cpus) or args.segments <= 0 or args.repeats <= 0:
        a.error('Require positive segments, repeats and available worker counts')
    configure(args.repo.resolve())
    reference=oracle(args.order,args.segments)
    rng=random.Random(25473); trace=None
    for repeat in range(args.repeats):
        cases=[(p,l,m) for p in args.ranks for l in (['rows'] if p==1 else args.layouts)
               for m in (['conservative'] if p==1 else args.modes)]
        rng.shuffle(cases)
        for count,layout,mode in cases:
            data=trial(cpus,args.order,count,layout,mode,args.segments,args.window)
            if trace is None: trace=data['emitted']
            if data['digest'] != reference or data['emitted'] != trace:
                raise ValueError('Cavity prefix differs from the serial state or event trace')
            data.update(repeat=repeat+1,oracle_sha256=reference)
            print(json.dumps(data,separators=(',',':')),flush=True)
