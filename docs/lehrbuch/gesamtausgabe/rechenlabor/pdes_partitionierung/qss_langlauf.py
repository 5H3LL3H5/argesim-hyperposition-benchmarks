"""Componentwise CP2 QSS3/4 with the book's root isolator and restartable full-horizon integration."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import signal
import sys
import time
from pathlib import Path
from zipimport import zipimporter

import numpy as np
from vollgitter import CHECKS, DT, END, PREFIX, RE, N

QUANTUM = 0.001
FINAL = END * DT
ROOT_TOL = 1e-12
STENCILS = {
    3: ((12, (8, -1)), (24, (16, -1))),
    4: ((60, (45, -9, 1)), (360, (270, -27, 2)), (48, (-13, 8, -1))),
}


def physics(repo):
    archive = repo / 'docs/lehrbuch/gesamtausgabe/pakete/Laborquellen.zip'
    member = PREFIX + 'basis/kavitaet.py'
    offline = repo / PREFIX / 'basis/original'
    sys.path.insert(0, str(offline if offline.is_dir() else repo))
    if archive.exists():
        loader = zipimporter(str(archive / Path(member).parent))
        spec = loader.find_spec('kavitaet')
    else:
        spec = importlib.util.spec_from_file_location('kavitaet', repo / member)
    if spec is None or spec.loader is None:
        raise ImportError(f'Missing cavity model in {member}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from argesim_benchmarks.solvers.advanced_qss import _boundary_time
    return module.Cavity(N, RE), _boundary_time


def value(poly, dt):
    result = poly[-1]
    for coefficient in poly[-2::-1]:
        result = result * dt + coefficient
    return result


def shift(poly, dt):
    # Preserve the reference's ascending summation order and power evaluation.
    return np.array([sum(poly[j] * math.comb(j, k) * dt ** (j-k)
                         for j in range(k, len(poly))) for k in range(len(poly))])


def continuous(cavity, t, state, q):
    order = len(q)
    radius = order - 1
    scale = max(1., float(np.max(np.abs(q[0]))))
    length = 1.
    for power in range(1, order):
        peak = float(np.max(np.abs(q[power])))
        if peak:
            length = min(length, (scale / peak) ** (1. / power))
    step = math.ldexp(1., math.frexp(sys.float_info.epsilon ** (1. / (2*order-1)) * length)[1] - 1)
    samples = [cavity.rhs(t + j*step, value(q, j*step)) for j in range(-radius, radius+1)]
    centre = samples[radius]
    rows = [state, centre]
    for power, (denom, weights) in enumerate(STENCILS[order], 1):
        terms = []
        for j, weight in enumerate(weights, 1):
            upper, lower = samples[radius+j], samples[radius-j]
            pair = upper-lower if power % 2 else (upper-centre) + (lower-centre)
            terms.append(weight * pair)
        if len(terms) == 2:
            summed = terms[0] + terms[1]
        else:
            summed = np.fromiter(map(math.fsum, zip(*terms)), dtype=float, count=len(state))
        coefficient = summed / denom
        for _ in range(power):
            coefficient /= step
        rows.append(coefficient / (power+1))
    x = np.array(rows)
    if not np.isfinite(x).all():
        raise ArithmeticError('Non-finite Taylor coefficients')
    return x


def contacts(x, q, now, previous, root):
    """Screen with an outward-padded triangle bound, solve survivors on the full interval."""
    remain = FINAL - now
    tol = ROOT_TOL * max(1., abs(now))
    interval = min(remain, max(4*previous, 4*tol))
    delta = x.copy()
    delta[:-1] -= q
    magnitudes = np.abs(delta)
    times = np.full(x.shape[1], math.inf)
    checked = np.zeros(x.shape[1], dtype=bool)
    while True:
        # Include all components that could be simultaneous with a contact at interval.
        margin = 4 * ROOT_TOL * max(1., abs(now+interval))
        probe = min(remain, interval+margin)
        bound = value(magnitudes, probe)
        candidates = (bound >= QUANTUM * (1 - 32*sys.float_info.epsilon)) & ~checked
        for i in np.flatnonzero(candidates):
            times[i] = root(x[:, i].tolist(), q[:, i].tolist(), QUANTUM, remain, tol)
        checked |= candidates
        first = float(times.min())
        if first <= interval or interval == remain:
            if first >= remain:
                return remain, np.empty(0, dtype=int)
            threshold = ROOT_TOL * max(1., abs(now+first), abs(first))
            return first, np.flatnonzero(abs(times-first) <= threshold)
        interval = min(remain, 2*interval)


def checkpoint(path, **state):
    tmp = path.with_suffix('.tmp')
    with tmp.open('wb') as target:
        np.savez(target, **state)
    os.replace(tmp, path)


def run(args):
    cavity, root = physics(args.repo.resolve())
    directory = args.output
    directory.mkdir(parents=True, exist_ok=True)
    state_path = directory / 'restart.npz'
    source_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    configuration = json.dumps([N, RE, END, QUANTUM, args.order, source_hash])
    last_report = start = time.perf_counter()
    done = False

    def stopping(_signal, _frame):
        nonlocal done
        done = True

    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGINT, stopping)
    if args.resume:
        with np.load(state_path, allow_pickle=False) as saved:
            recorded = json.loads(str(saved['config']))
            expected = json.loads(configuration)
            if recorded != expected:
                # Only verified bitwise-equivalent integrator revisions can share a checkpoint.
                migrations = json.loads(Path(__file__).with_name('restart_kompatibilitaet.json').read_text())
                if recorded[:-1] != expected[:-1] or [recorded[-1], source_hash] not in migrations:
                    raise ValueError('Restart belongs to a different experiment')
            now, previous, spent = map(float, (saved['now'], saved['previous'], saved['wall_s']))
            segments, events, next_mark = map(int, (saved['segments'], saved['events'], saved['next_mark']))
            x, q = saved['x'], saved['q']
    else:
        if state_path.exists():
            raise FileExistsError('Use --resume or a new output directory')
        q = np.zeros((args.order, cavity.dim))
        initial = np.zeros(cavity.dim)
        for _ in range(args.order):
            x = continuous(cavity, 0., initial, q)
            q[1:] = x[1:-1]
        x = continuous(cavity, 0., initial, q)
        now = spent = 0.
        previous = DT
        segments = events = next_mark = 0

    with (directory / 'progress.jsonl').open('a' if args.resume else 'w', buffering=1) as log:
        while now < FINAL and not done:
            elapsed, due = contacts(x, q, now, previous, root)
            next_time = FINAL if elapsed == FINAL-now else now+elapsed
            if next_time <= now:
                raise ArithmeticError('No advance in simulation time')
            while next_mark < len(CHECKS) and CHECKS[next_mark]*DT <= next_time:
                tick = CHECKS[next_mark]
                field = value(x, tick*DT-now)
                if not np.isfinite(field).all():
                    raise ArithmeticError('Non-finite observation')
                field.astype('<f8').tofile(directory / f'z_{tick}.bin')
                next_mark += 1
            x = shift(x, elapsed)
            q = shift(q, elapsed)
            now, previous = next_time, elapsed
            segments += 1
            events += len(due)
            if args.trace and segments <= args.trace:
                digest = hashlib.sha256(x[0].astype('<f8').tobytes()).hexdigest()
                log.write(json.dumps({'trace': segments, 't_star': now, 'field_sha256': digest, 'due': due.tolist()})+'\n')
            if now < FINAL:
                q[:, due] = x[:-1, due]
                x = continuous(cavity, now, x[0], q)
            stamp = time.perf_counter()
            done = done or (args.stop_after is not None and segments >= args.stop_after)
            if done or now == FINAL or stamp-last_report >= args.checkpoint_seconds or segments == 1:
                wall = spent+stamp-start
                checkpoint(state_path, config=configuration, now=now, previous=previous, segments=segments,
                           events=events, next_mark=next_mark, wall_s=wall, x=x, q=q)
                progress = {'order': args.order, 'segments': segments, 'events': events, 't_star': now,
                                'equivalent_ticks': now/DT, 'target_ticks': END, 'wall_s': wall,
                                'observations': next_mark, 'complete': (now == FINAL)}
                log.write(json.dumps(progress)+'\n')
                print(json.dumps(progress), flush=True)
                last_report = stamp


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--order', choices=(3, 4), type=int, required=True)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--trace', type=int, default=0)
    parser.add_argument('--stop-after', type=int, help='explicit diagnostic segment count')
    parser.add_argument('--checkpoint-seconds', type=float, default=60.)
    args = parser.parse_args()
    sys.exit(run(args))
