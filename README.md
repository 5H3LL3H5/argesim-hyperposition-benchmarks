# ARGESIM and NSA-DEVS reference suite

This branch is the scientific rebuild of the historical repository. It has
two deliberately separate purposes:

1. provide executable reference semantics for restricted NSA-DEVS timing;
2. implement and validate the official ARGESIM catalog without relabelling
   unrelated toy problems as ARGESIM benchmarks.

## Current status

The official inventory is complete for the catalog published in August 2026:
C01-C22 plus CP1 and CP2. C17R and C19R are the active revised definitions.
The inventory is machine-readable in `argesim_benchmarks.catalog`.

ARGESIM C01 is the first model at the `implemented` gate.
ARGESIM C17R is the second model at the `implemented` gate. The remaining 22
definitions are cataloged only. Each benchmark must pass five evidence gates
before it is benchmark-ready:

`cataloged -> specified -> implemented -> validated -> benchmark-ready`

See [ARGESIM_COVERAGE.md](ARGESIM_COVERAGE.md) for the per-model status.

## Implemented numerical foundation

- fixed-step explicit Euler;
- fixed-step classical RK4;
- adaptive Dormand-Prince RK45 with a 5(4) embedded error estimate;
- asynchronous first-order QSS for autonomous ODE systems;
- asynchronous second-order QSS2 using a scaled directional finite difference;
- bracketed Brent root finding with explicit non-convergence reporting;
- one-dimensional heat and wave equations through the Method of Lines;
- exact rational macro time plus integer microsteps and a deterministic DES
  scheduler for restricted NSA-DEVS;
- a finite acyclic Mealy-style NSA-DEVS relay reference model.
- ARGESIM C01 tasks A-C, including the official parameter sweep and analytical
  steady states.
- ARGESIM C17R (ODE part) task 1 parameters, ODE problem, and solvers.

LIQSS, DAE handling, general hybrid-event localization, the modern
`neuraloperator` backend and ARGESIM C02-C22/CP1/CP2 are tracked as work in
progress. They are not silently mapped to simpler algorithms.

## Run the tests

No third-party Python dependency is required for the current reference core.

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

## Run the NSA-DEVS experiments

```bash
python benchmarks/benchmark_event_chain.py --length 1000 --repeat 21
python benchmarks/benchmark_euler_convergence.py
python benchmarks/benchmark_argesim_c01.py --repeat 9 --warmup 1
```

The event-chain benchmark validates result parity before recording timing. It
reports median and interquartile range and makes no speedup claim.

## Interpretation

`HyperTime` is an executable superdense-time encoding of values `a + b epsilon`
needed by the restricted reference model. It is not an implementation of the
complete hyperreal field. QSS is a DEVS-based numerical method, but its use
does not by itself establish any claim about locks, rollbacks or parallel
speedup.
