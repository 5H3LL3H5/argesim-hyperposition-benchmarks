"""Follow-up to chapter exercises: dense-output certificates, hybrid events and selection."""

from __future__ import annotations

import csv
import itertools
import json
import math
from pathlib import Path

import mpmath as mp
import numpy as np
from scipy.integrate import solve_ivp
from scipy.special import lambertw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/lehrbuch/studienbuch/material/cp2_genauigkeit"
iv = mp.iv
iv.dps = 35


def upper(x):
    return math.nextafter(float(x.b), math.inf)


def dense_value(segment, method, t):
    start = iv.mpf(float(segment.t_old))
    if method == "BDF":
        val = iv.mpf(float(segment.D[-1, 0]))
        for i in reversed(range(segment.order)):
            z = (t - float(segment.t_shift[i])) / float(segment.denom[i])
            val = float(segment.D[i, 0]) + z * val
        return val
    z = (t - start) / float(segment.h)
    val = iv.mpf(0)
    for q in reversed(segment.Q[0]):
        val = (val + float(q)) * z
    if method == "RK45":
        val *= float(segment.h)
    return float(segment.y_old[0]) + val


def dense_bounds():
    # Degree-five Bernstein interpolation at six equidistant rational nodes.
    mat = iv.matrix(6)
    for i, j in itertools.product(range(6), repeat=2):
        x = iv.mpf(i) / 5
        mat[i, j] = math.comb(5, j) * x**j * (1 - x) ** (5 - j)
    transform = mat**-1

    def rhs(t, y):
        return -np.sin(t) + 1000 * (np.cos(t) - y)

    rows = []
    for method, tol in itertools.product(["RK45", "Radau", "BDF"], [1e-3, 1e-6]):
        opts = {} if method == "RK45" else {"jac": np.array([[-1000.0]])}
        sol = solve_ivp(
            rhs,
            (0.0, 2.0),
            [0.0],
            method=method,
            rtol=tol,
            atol=tol / 100,
            dense_output=True,
            **opts,
        )
        assert sol.success
        highest = 0
        node_lower = 0
        boxes = 0
        for seg in sol.sol.interpolants:
            start = iv.mpf(float(seg.t_old))
            width = iv.mpf(float(seg.t)) - start
            deriv6 = 1 + 10**18 * iv.exp(-1000 * start)
            n = max(
                1, math.ceil(float(width.b) * (upper(deriv6) / (720 * 2e-9)) ** (1 / 6))
            )
            h = width / n
            for j in range(n):
                values = iv.matrix(6, 1)
                for i in range(6):
                    t = start + h * (j + iv.mpf(i) / 5)
                    values[i] = (
                        dense_value(seg, method, t) - iv.cos(t) + iv.exp(-1000 * t)
                    )
                    node_lower = max(
                        node_lower, math.nextafter(float(abs(values[i]).a), -math.inf)
                    )
                coeff = transform * values
                highest = max(
                    highest, upper(max(abs(v).b for v in coeff) + deriv6 * h**6 / 720)
                )
                boxes += 1
        rows.append(
            {
                "method": method,
                "rtol": tol,
                "steps": len(sol.t) - 1,
                "lower": node_lower,
                "upper": highest,
                "boxes": boxes,
            }
        )
    return rows


def threshold_box():
    # Independent intervals for both thresholds on every phase (conservative).
    upper_th = iv.mpf(["5.795", "5.805"])
    lower_th = iv.mpf(["2.495", "2.505"])
    state = (iv.mpf("4.2"), iv.mpf(".3"))
    clock = iv.mpf(0)
    records = []
    fast = iv.mpf("2700000")
    slow = iv.mpf("3.5651205")
    for index in range(4):
        sign = 1 if index % 2 == 0 else -1
        offset, target, guard = (
            (iv.mpf(".4"), iv.mpf("5.5"), upper_th)
            if sign == 1
            else (iv.mpf("-.3"), iv.mpf("2.73"), lower_th)
        )
        a = (state[1] - target) * fast / (fast - slow)
        b = state[0] - target - offset - a

        def signed(t, sign=sign, target=target, offset=offset, a=a, b=b, guard=guard):
            return sign * (
                target + offset + a * iv.exp(-slow * t) + b * iv.exp(-fast * t) - guard
            )

        assert signed(iv.mpf(0)).b < 0 and signed(iv.mpf(2)).a > 0
        intervals = []
        for endpoint in ["b", "a"]:
            lo, hi = iv.mpf(0), iv.mpf(2)
            for _ in range(42):
                mid = (lo + hi) / 2
                if getattr(signed(mid), endpoint) < 0:
                    lo = mid
                else:
                    hi = mid
            intervals.append(lo if endpoint == "b" else hi)
        duration = iv.mpf([intervals[0].a, intervals[1].b])
        clock += duration
        slope = sign * (
            -slow * a * iv.exp(-slow * duration) - fast * b * iv.exp(-fast * duration)
        )
        assert slope.a > 0
        records.append(
            [
                math.nextafter(float(clock.a), -math.inf),
                upper(clock),
                math.nextafter(float(slope.a), -math.inf),
            ]
        )
        state = (guard, target + (state[1] - target) * iv.exp(-slow * duration))
    return records


def diode():
    # b=u_C+R2*i. Resolvent residues for input source and additive diode current.
    R = iv.mpf(20)
    L = iv.mpf(".0000253")
    C = iv.mpf(".0000001")
    UT = iv.mpf(".026")
    Is = iv.mpf(".00000001")
    w = 2 * iv.pi * 150000
    A = iv.matrix([[-1020 / L, -1 / L], [1 / C, 0]])
    obs = iv.matrix([[R, 1]])
    disc = iv.sqrt((1020 / L) ** 2 - 4 / (L * C))
    rates = [(-1020 / L + disc) / 2, (-1020 / L - disc) / 2]

    def residues(B):
        return [
            (obs * (A - rates[1 - j] * iv.eye(2)) * B)[0] / (r - rates[1 - j])
            for j, r in enumerate(rates)
        ]

    source = residues(iv.matrix([1 / L, 0]))
    current = residues(iv.matrix([-R / L, 1 / C]))
    b_s = sum(2 * abs(s) / iv.sqrt(w * w + r * r) for s, r in zip(source, rates))
    gain = sum(abs(s) / (-r) for s, r in zip(current, rates))
    cap = iv.mpf(".1")
    dmax = Is * (iv.exp(cap / UT) - 1)
    b_bound = b_s + gain * dmax
    assert b_bound.b < (cap - R * dmax).a
    deriv = 1 - R * Is / UT * iv.exp(cap / UT)

    # Independent off-grid trajectory using the principal real Lambert-W branch.
    def voltage(b):
        q = b - 2e-7
        return np.where(
            b <= 0, b, q - 0.026 * lambertw(-2e-7 / 0.026 * np.exp(q / 0.026)).real
        )

    def rhs(t, y):
        i, uc = y
        z = voltage(uc + 20 * i)
        d = np.expm1(max(0.0, z) / 0.026) * 1e-8
        return [
            (-np.sin(2 * np.pi * 150000 * t) - 1000 * i - z) / 25.3e-6,
            (i + d) / 1e-7,
        ]

    def guard(t, y):
        return y[1] + 20 * y[0]

    sol = solve_ivp(
        rhs,
        (0, 5e-4),
        [0.0, 0.0],
        method="Radau",
        rtol=1e-9,
        atol=[1e-12, 1e-10],
        max_step=8e-8,
        dense_output=True,
        events=guard,
    )
    assert sol.success
    times = np.random.default_rng(3267).uniform(0, 5e-4, 6013)
    i, uc = sol.sol(times)
    return {
        "source_bound": upper(b_s),
        "gain_ohm": upper(gain),
        "b_bound_V": upper(b_bound),
        "derivative_lower": math.nextafter(float(deriv.a), -math.inf),
        "probe_max_V": float(voltage(uc + 20 * i).max()),
        "noninitial_crossings": int(sum(sol.t_events[0] > 1e-12)),
    }


def cartesian():
    g = np.array([0.0, -9.81])
    ray = np.array([np.sin(-np.pi / 12), -np.cos(-np.pi / 12)])
    normal = np.array([-ray[1], ray[0]])
    state = np.array([0.5, -np.cos(np.pi / 6), 0.0, 0.0])
    length = 1.0
    start = 0.0
    hits = []
    max_len = max_tan = 0.0
    while start < 10:
        pivot = (1 - length) * ray

        def rhs(t, q, pivot=pivot, length=length):
            s, v = q[:2] - pivot, q[2:]
            return np.r_[v, g - (v @ v + s @ g) * s / length**2 - 0.2 / 1.02 * v]

        def event(t, q, pivot=pivot):
            return normal @ (q[:2] - pivot)

        event.terminal = True
        event.direction = -1 if length == 1 else 1
        sol = solve_ivp(
            rhs,
            (start, 10.0),
            state,
            method="DOP853",
            rtol=1e-11,
            atol=1e-13,
            max_step=0.02,
            events=event,
        )
        assert sol.success
        pos = sol.y[:2].T - pivot
        vel = sol.y[2:].T
        max_len = max(max_len, float(abs(np.linalg.norm(pos, axis=1) - length).max()))
        max_tan = max(max_tan, float(abs((pos * vel).sum(1)).max()))
        if not len(sol.t_events[0]):
            break
        start = sol.t_events[0][0]
        before = sol.y_events[0][0]
        state = before.copy()
        length = 0.3 if length == 1 else 1.0
        s = state[:2] - (1 - length) * ray
        hits.append(
            {
                "time": float(start),
                "new_length_error": float(abs(np.linalg.norm(s) - length)),
                "new_tangency": float(abs(s @ state[2:])),
                "impulse_jump": float(1.02 * np.linalg.norm(state[2:] - before[2:])),
            }
        )
        assert len(hits) <= 10
    # Angle integration uses the lab's independently implemented 2-state formulation.
    import importlib.util

    spec = importlib.util.spec_from_file_location("course_lab", OUT.parent / "labor.py")
    lab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lab)
    other, _ = lab.c07()
    return {
        "hits": hits,
        "max_length": max_len,
        "max_tangency": max_tan,
        "max_event_time": float(np.max(abs(other[:, 0] - [h["time"] for h in hits]))),
    }


def selection():
    with (ROOT / "docs/evidence/qss-selection.csv").open() as fh:
        rows = [r for r in csv.DictReader(fh) if r["case"].startswith("C")]
    cases = sorted({r["case"] for r in rows})
    # Only configurations present exactly once on every case are eligible. Rank
    # failures after successes and compare relative cost to the fastest valid row.
    keys = sorted(
        set.intersection(
            *[
                {(r["method"], r["level"]) for r in rows if r["case"] == c}
                for c in cases
            ]
        )
    )
    table = {(r["case"], r["method"], r["level"]): r for r in rows}

    def cost(c, key):
        r = table[(c, *key)]
        if r["status"] != "pass":
            return None
        best = min(
            float(table[(c, *k)]["median_ms"])
            for k in keys
            if table[(c, *k)]["status"] == "pass"
        )
        return float(r["median_ms"]) / best

    results = []
    for test in cases:

        def score(k, test=test):
            costs = [cost(c, k) for c in cases if c != test]
            valid = [z for z in costs if z is not None]
            return (len(costs) - len(valid), np.mean(valid) if valid else np.inf, k)

        chosen = min(keys, key=score)
        results.append(
            {
                "case": test,
                "method": chosen[0],
                "level": chosen[1],
                "cost_ratio": cost(test, chosen),
            }
        )
    return {"candidates": len(keys), "folds": results}


if __name__ == "__main__":
    reports = {
        "dense": dense_bounds(),
        "thresholds": threshold_box(),
        "diode": diode(),
        "cartesian": cartesian(),
        "selection": selection(),
    }
    (OUT / "kapitel.json").write_text(
        json.dumps(reports, indent=2, allow_nan=False) + "\n"
    )
