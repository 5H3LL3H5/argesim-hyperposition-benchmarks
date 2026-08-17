# ARGESIM and NSA-DEVS reference suite

This branch is the scientific rebuild of the historical repository. It has
two deliberately separate purposes:

1. provide executable reference semantics for restricted NSA-DEVS timing;
2. implement and validate the official ARGESIM catalog without relabelling
   unrelated toy problems as ARGESIM benchmarks.

## Current status

The official inventory was re-audited on 2026-08-17: C01-C22 plus CP1 and
CP2, with C17R and C19R as the active revised definitions. The machine-readable
inventory in `argesim_benchmarks.catalog` records the evidence reached by each
complete task family instead of treating file presence as implementation.

C02, C05, C08, C21, CP1 and CP2 currently reach the `validated` gate. Every
other catalog family reaches `implemented`: all required task types have an
executable path, while independent external full-output references are still
missing for several families. Each benchmark must pass five evidence gates:

`cataloged -> specified -> implemented -> validated -> benchmark-ready`

See [ARGESIM_COVERAGE.md](ARGESIM_COVERAGE.md) for the per-model status and
[ARGESIM_AUDIT.md](ARGESIM_AUDIT.md) for the definition-by-definition review.

## Implemented numerical foundation

- fixed-step explicit Euler;
- fixed-step classical RK4;
- adaptive Dormand-Prince RK45 with a 5(4) embedded error estimate;
- asynchronous first-order QSS for autonomous ODE systems;
- asynchronous second-order QSS2 using a scaled directional finite difference;
- bracketed Brent root finding with explicit non-convergence reporting;
- one strict solver dispatcher shared by model wrappers, including segmented
  non-autonomous inputs;
- directed state-event localization (cubic-Hermite dense guards for classical
  steps) and mode/state resets shared by classical and QSS backends, including
  dimension-changing transitions;
- one-dimensional heat and wave equations through the Method of Lines;
- exact rational macro time plus integer microsteps and a deterministic DES
  scheduler with cancellation, finite horizons, idle draining and event caps;
- a finite acyclic Mealy-style NSA-DEVS relay reference model;
- a reusable ordered serial/thread/process execution and timing layer;
- complete C04 fairness/deadlock statistics, exact C05 event references,
  reference-convention C09 fuzzy control, FHP-I/random-movement C17R,
  C18 ARX/static/dynamic ANN identification, dimensioned C20 transport and
  all C21 event/pendulum/diode forms;
- complete CP1 and CP2 workload entry points, including D2Q9 LBGK and an
  implicit string solver checked against its Fourier series and the corrected
  published `nu=0.06` parameter set;
- executable benchmark modules at the evidence gates listed above.

LIQSS, a general-purpose implicit DAE solver and a trained neural-operator
backend remain explicit non-goals. C21 implements the benchmark's specified
index-1 reduction; it is not silently presented as a general DAE facility.

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
