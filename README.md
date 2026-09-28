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
- dependency-free QSS3 and QSS4 polynomial quantizers with exact low-degree
  event-root isolation;
- LIQSS1/2/3 and mLIQSS1/2/3 for stiff autonomous ODEs, with an optional exact
  Jacobian and a checked dense finite-difference fallback;
- eLIQSS1/2/3 and CheQSS1/2/3 with published generalized difference
  polynomials, planned self-events and cross-state error guards;
- published first-order centered CQSS for suitable Hamiltonian systems, with
  explicit detection of its no-hysteresis zero-time cycles;
- partitioned LIQSS2-BDF mixed-mode integration with persistent quantizer
  state, linear interfaces and an independent adaptive BDF1/2 backend;
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

A general-purpose implicit DAE solver and a trained neural-operator backend
remain explicit non-goals. LIQSS handles stiff ODE structure; it does not turn
an algebraic system into an ODE. C21 implements the benchmark's specified
index-1 reduction and is not silently presented as a general DAE facility.

See [QSS_SOLVERS.md](QSS_SOLVERS.md) for solver selection, Jacobian contracts,
the mLIQSS3 status and the assessment of the external CIFASIS engine. The dated
[QSS state-of-the-art matrix](QSS_STATE_OF_THE_ART.md) separates numerical
families, quantum policies and execution architectures.

## Run the tests

No third-party Python dependency is required for the current reference core.

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

## Run the registered benchmark suite

```bash
argesim run-suite --profile smoke
argesim run-suite --profile definition
argesim run-suite --profile smoke --benchmark C19R --benchmark C22
```

The JSON report lists each task's input arguments, outcome, elapsed time and
error, if any. A failure gives a nonzero exit code; later tasks still run unless
`--fail-fast` is set. The smoke profile shortens costly workloads, and the
definition profile uses the documented task defaults (including long CP2 LBM
runs). Passing a suite run proves execution only; published reference checks
and catalog evidence gates are assessed separately.

Each task also contains a versioned `evidence` object. Its nested
`experiment` records the Git commit (when available), effective arguments
including defaults, scalar seed (when supplied), UTC capture time, elapsed
time, Python/OS/CPU environment and nullable validation and work counters.
The surrounding record gives the UTC start, status, failure text and reasons
for unavailable fields. `scope` remains `execution only`: a successful task
does not establish an independent oracle match or a performance result.
The one elapsed time sample has no defined IQR. Per-task Python allocation
and RSS peaks are not measured by this execution command; they remain null.
Set `ARGESIM_GIT_SHA` when running from a source export without Git metadata.

## Run the NSA-DEVS experiments

```bash
python benchmarks/benchmark_event_chain.py --length 1000 --repeat 21
python benchmarks/benchmark_euler_convergence.py
python benchmarks/benchmark_argesim_c01.py --repeat 9 --warmup 1
python benchmarks/benchmark_qss_variants.py --repeat 9 --warmup 1
python benchmarks/benchmark_cqss_liqss_bdf.py --repeat 9 --warmup 1
```

The event-chain benchmark validates result parity before recording timing. It
reports median and interquartile range and makes no speedup claim.

## Interpretation

`HyperTime` is an executable superdense-time encoding of values `a + b epsilon`
needed by the restricted reference model. It is not an implementation of the
complete hyperreal field. QSS is a DEVS-based numerical method, but its use
does not by itself establish any claim about locks, rollbacks or parallel
speedup.
