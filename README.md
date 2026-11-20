# ARGESIM and NSA-DEVS reference suite

This branch is the scientific rebuild of the historical repository. It has
two deliberately separate purposes:

1. provide executable reference semantics for restricted NSA-DEVS timing;
2. implement and validate the official ARGESIM catalog without relabelling
   unrelated toy problems as ARGESIM benchmarks.

## Current status

The catalog contains 24 families, including revised definitions C17R and C19R.
Twelve have numerical reference checks for identified cases. Eleven have
executable implementations. C18 has executable identification algorithms and
digitized examples. It remains at `specified` pending the two original recordings.
The catalog records the following evidence gates.

`cataloged -> specified -> implemented -> validated -> benchmark-ready`

The [published comparisons](docs/PUBLISHED_REFERENCE_CHECKS.md) give the tested cases, numerical differences and remaining evidence for all 24 families.
See [ARGESIM_COVERAGE.md](ARGESIM_COVERAGE.md) for the per-model status and
[ARGESIM_AUDIT.md](ARGESIM_AUDIT.md) for the definition-by-definition review.
The [2026-11-19 transport/data report](docs/ARGESIM_TRANSPORT_DATA_20261119.md)
records the C20 geometry, controller, test scope and C18 input-data contract.
The [2026-11-20 corrective report](docs/ARGESIM_CLOSURE_20261120.md) adds C02
routing fixes, C18 numerical verification and the reproducible C20 study.
The [C02 implementation report](C02_IMPLEMENTATION.md) gives the subsequent
1–60 pallet study, deadlock evidence, seeded initial positions and finite-window
accounting. The [C18 figure experiment](docs/C18_FIGURE_RECONSTRUCTION.md)
records the reconstructed signals, two published linear-model correlations
and free-running predictions after recurrent network training.

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
and catalog evidence gates are assessed separately. C18 smoke explicitly uses
the labelled figure-reconstruction demo. A regular C18 run requires both data
sets (objects or CSV paths); missing measurements fail instead of silently
loading substitutes.

Each task also contains a versioned `evidence` object. Its nested
`experiment` records the Git commit (when available), effective arguments
including defaults, scalar seed (when supplied), UTC capture time, elapsed
time, Python/OS/CPU environment and nullable validation and work counters.
The surrounding record gives the UTC start, status, failure text and reasons
for unavailable fields. `scope` remains `execution only`: a successful task
does not establish an independent oracle match or a performance result.
The one elapsed time sample has no defined IQR. Per-task Python allocation
and RSS peaks are not measured by this execution command; they remain null.
An uncommitted source tree reports a null SHA rather than attributing the run
to stale `HEAD`. Set `ARGESIM_GIT_SHA` only when the source export has been
verified against that exact commit.

## Repeated diagnostic timing

Run a selected task in a fresh subprocess and write its evidence into a new
empty directory:

```bash
argesim run-performance --profile smoke --benchmark C01 --task C01:C \
  --warmup 1 --repetitions 9 --output-dir benchmark-results/c01-diagnostic
```

`--profile definition` is the default and may invoke very large official
workloads. Repetitions must be odd and at least nine; warm-up is configurable.
`--benchmark` and `--task BENCHMARK:TASK` can be repeated; `--fail-fast` stops
after the first failure, while the default continues. `--timeout-s` defaults
to 3600 per task. Each task produces an atomically written JSON record, and
`manifest.json` records artifact paths, statuses and SHA-256 digests. The
output directory must be empty; local `benchmark-results/` is ignored by Git.

The worker compares a complete JSON result fingerprint against an untimed
reference before publishing a median or inclusive IQR. All raw durations are
kept; if parity fails, the summary stays null and the run fails. Exact parity
can reject tasks whose outputs contain volatile timing data or unconstrained
randomness; that is a documented blocker, not a result match. The independent
validation fields remain null, so these numbers are **diagnostic timings**,
including when definition inputs are selected. Smoke inputs are reduced and
must never be presented as official benchmark performance.

Python peak allocation is collected in a separate untimed `tracemalloc`
probe. Peak RSS comes from the fresh worker's process high-water mark *before*
that probe, including interpreter and imports. Linux `ru_maxrss` is reported
in KiB and converted to bytes; macOS reports bytes; unknown units produce
null with a reason. The RSS high-water mark covers the fresh benchmark worker
process, not child processes created by parallel tasks. Work counters are
recorded per repetition only for a directly returned `IntegrationResult`;
unknown counters stay null. No catalog evidence gate is
changed by repeated execution or internal parity alone.

## Optional external solver oracle

The suite defines a process-isolated protocol for an independently installed
[`CIFASIS/qss-solver`](https://github.com/CIFASIS/qss-solver/tree/qss-solver-dev)
adapter. The initial boundary records capabilities, pinned engine and suite
commits, request/model hashes, bounded process diagnostics and checksummed
artifacts. It does not copy or link CIFASIS code. The repository ships a
narrow native adapter and deterministic micro-Modelica translation for an
analytic scalar linear-decay pilot. Only QSS1 and QSS2 are advertised by this
first adapter delta; no ARGESIM benchmark or additional QSS-family method is
thereby qualified:

```bash
argesim oracle probe cifasis
export ARGESIM_CIFASIS_SOURCE=/path/to/pinned/qss-solver
export ARGESIM_CIFASIS_ROOT=/path/to/qss-solver-install
argesim oracle run cifasis \
  --request examples/cifasis-linear-decay-qss2.json \
  --output-dir results/cifasis-linear-decay-qss2
```

An absent adapter produces a structured `unavailable` result. A successful
external execution is a cross-engine observation, not independent validation,
a speedup result or an ARGESIM evidence-gate promotion. See
[the adapter contract](docs/CIFASIS_ORACLE.md).

The pinned native engine has been built and exercised for both pilot methods.
At the emitted sample times, QSS1 and QSS2 satisfy the requested analytic error
budget. QSS2 does not emit a sample exactly at the requested stop time, which
is reported separately from sample-point accuracy. The dated machine-readable
record is in
[`docs/evidence/cifasis-linear-decay-20260928.json`](docs/evidence/cifasis-linear-decay-20260928.json).

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

## Discrete-event ordering

`DesScheduler.schedule` and `schedule_at` accept a keyword-only integer
`priority` (default `0`). Pending events are ordered by macro time, microstep,
priority, then insertion sequence. Lower priority numbers run first at the
same exact `HyperTime`; equal priorities preserve FIFO order. Existing calls
therefore retain their ordering. Priority never overrides macro time or a
causal microstep, and zero-delay `schedule` calls still advance the microstep.

Models must choose their own simultaneous-event policy. For example, queue an
abort at priority `-1` and a result at priority `0` at the same time to process
the abort first while still accounting for the result. This applies to pending
events only: an event inserted by a callback cannot run before that callback,
and late external arrivals cannot undo completed handlers. The scheduler does
not provide network-arrival independence or automatic confluent transitions.

Both run methods count executed callbacks toward `max_events`; cancelled
entries are discarded without consuming that budget or advancing time.

## Interpretation

`HyperTime` is an executable superdense-time encoding of values `a + b epsilon`
needed by the restricted reference model. It is not an implementation of the
complete hyperreal field. QSS is a DEVS-based numerical method, but its use
does not by itself establish any claim about locks, rollbacks or parallel
speedup.
