"""Compare contacts and full fields against the independent dense reference on the 257 grid."""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from qss_langlauf import DT, FINAL, QUANTUM, contacts, continuous, physics, shift


def check(repo, order, segments):
    cavity, root = physics(repo)
    from argesim_benchmarks import InitialValueProblem, solve_ivp
    times = []
    fields = []
    def record(_t0, _y0, t1, y1):
        times.append(t1)
        fields.append(np.array(y1))
        return len(times) == segments
    problem = InitialValueProblem(cavity.rhs, 0., (0.,)*cavity.dim, FINAL,
                                  autonomous=True, _stop_after_step=record)
    solve_ivp(problem, method=f'qss{order}', options={'quantum':QUANTUM})
    state = np.zeros(cavity.dim)
    q = np.zeros((order,cavity.dim))
    for _ in range(order):
        x = continuous(cavity,0.,state,q)
        q[1:] = x[1:-1]
    x = continuous(cavity,0.,state,q)
    t = 0.
    previous = DT
    max_dt = max_field = 0.
    for expected_time, expected_field in zip(times,fields,strict=True):
        elapsed, due = contacts(x,q,t,previous,root)
        t += elapsed
        previous = elapsed
        x, q = shift(x,elapsed), shift(q,elapsed)
        max_dt = max(max_dt, abs(t-expected_time))
        max_field = max(max_field, float(np.max(abs(x[0]-expected_field))))
        q[:,due] = x[:-1,due]
        x = continuous(cavity,t,x[0],q)
    if not (max_dt < 2e-12 and max_field < 2e-9):
        raise ValueError(f'Published trajectory mismatch: {max_dt}, {max_field}')
    # The scalar root isolator and the vectorized prefilter must retain a tangent.
    # x(s) = 4 Delta s(1-s) touches +Delta at 0.5 while both endpoints lie inside.
    tangency = np.array([[0.],[4*QUANTUM],[-4*QUANTUM],[0.]])
    duration, due = contacts(tangency,np.zeros((3,1)),0.,0.01,root)
    if not math.isclose(duration,.5,abs_tol=1e-10) or list(due) != [0]:
        raise ValueError('Grazing band contact lost')
    return {'order': order, 'segments': segments, 'max_abs_time': max_dt,
                'max_abs_z': max_field, 'tangent_time': duration}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('repo',type=Path)
    p.add_argument('--segments',type=int,default=32)
    a = p.parse_args()
    for degree in (3,4):
        print(json.dumps(check(a.repo.resolve(), degree, a.segments)),flush=True)
