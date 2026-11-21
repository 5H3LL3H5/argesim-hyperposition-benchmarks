# Benchmark methodology

## Evidence gates

| Catalog level | Evidence required |
|---|---|
| `cataloged` | Official identity, active revision and model family. |
| `specified` | Definition, parameters, event rules, inputs, tasks and required outputs. |
| `implemented` | Executable paths and tests for the required task types. |
| `validated` | A named observable agrees with an independent analytical, numerical or published reference under a declared criterion. Read the case report for the scope. |
| `benchmark-ready` | Validated results plus workload parity, recorded environment, warm-up, repeated measurements and retained raw results for a comparable experiment. |

The [coverage tables](ARGESIM_COVERAGE.md) are generated from the catalog and task registry. C18 illustrates the difference between an executable algorithm and a reproducible official workload. Its three identification methods run on supplied or reconstructed data, while the original training and validation recordings are missing. [C18 provenance](docs/C18_FIGURE_RECONSTRUCTION.md)

## Execution evidence

From the repository root, run a single task for its result, or run a suite for a JSON record of each attempt.

```sh
python -m argesim_benchmarks run C01 C
python -m argesim_benchmarks run-suite --profile smoke --benchmark C01
```

`run-suite` records the task entry point, supplied arguments, effective defaults when resolvable, scalar seed when available, UTC timestamps, elapsed time, environment and failure details. A single duration has no defined IQR. Fields without a measurement, such as per-task RSS or an independent validation metric, are null with a reason. Some tasks perform their own comparisons. The suite status itself reports whether the call completed. [Suite runner](argesim_benchmarks/runner.py)

For suite and performance records, automatic Git provenance requires a clean worktree rooted at the package source with the evidence module tracked at HEAD. Dirty trees and ordinary installed copies return a null SHA. For a verified source export, the caller can supply its exact commit in `ARGESIM_GIT_SHA`. [Evidence implementation](argesim_benchmarks/evidence.py)

## Diagnostic timing and parallel comparisons

```sh
python -m argesim_benchmarks run-performance --profile smoke --benchmark C01 --task C01:C \
  --warmup 1 --repetitions 9 --output-dir benchmark-results/c01-diagnostic
```

Choose a new or empty output directory for each invocation. The runner reserves it for exclusive use and starts a fresh worker per selected task. That worker fingerprints an untimed result, checks each warm-up and measured repetition for exact parity, then checks a separate allocation run. A successful task records the raw wall times, median and inclusive IQR. A failure retains available samples and error details. Results containing variable timing or random draws can fail the parity check. Each task JSON has a SHA-256 digest in the manifest. [Performance runner](argesim_benchmarks/performance.py)

The default profile is `definition`. Specify `smoke` for reduced workloads. The default is one warm-up, nine repetitions and a timeout of 3,600 s per task. Repetitions must be odd and at least nine. Peak Python allocation comes from an untimed `tracemalloc` probe. Peak RSS is the worker process high-water mark measured before that probe, including interpreter and imports. Child processes have separate memory use. Direct `IntegrationResult` outputs also supply accepted steps, rejections and RHS evaluations.

For serial/parallel comparisons, give both paths the same ordered inputs, callable and workload. CP1 and CP2 use the shared executor where tasks are parallelized. Record backend, worker count, parity tolerance, error, warm-up, all repetitions and the environment before interpreting speedup or efficiency. A single benchmark timing is specific to its implementation and machine. [Ordered execution and timing](argesim_benchmarks/parallel.py)

## Continuous, hybrid and spatial models

Compare solvers using the same equations, initial state, interval and observable. Evaluate independent dense output at the candidate's stored times, or interpolate onto a specified common grid. Compare both sides of a reset consistently. Use component-wise tolerances or physically meaningful scales and keep solver work counts alongside elapsed time. The strict dispatcher accepts method-specific options. Piecewise-constant forcing can be split into autonomous segments. Smooth time-dependent forcing requires a compatible backend. [Solver guide](QSS_SOLVERS.md)

The hybrid runtime compares directed guards at accepted step boundaries. At the first bracketing step it stops that solve. With localization enabled it finds a crossing on a cubic-Hermite interpolant using endpoint states and derivatives, chooses the earliest candidate, records the reset and continues in the selected mode. With localization disabled it switches at the accepted endpoint. A reset can change dimension or terminate integration. The outer `max_events` limits recorded transitions. A crossing hidden inside a step whose endpoint guards do not bracket it can be missed. [Hybrid runtime](argesim_benchmarks/hybrid.py) · [Event regressions](tests/test_hybrid_runtime.py)

For a PDE, record the domain, spatial grid, source discretization, boundary conditions, time integrator and observation locations. Vary space and time independently. C19R's local mesh study demonstrates that reducing the time step alone leaves the dominant spatial error at the tested location. C21's diode reductions are model-specific. The repository supplies ODE solvers and those reductions. General high-index DAEs require a separate solver. [C19R study](docs/PUBLISHED_REFERENCE_CHECKS.md#c19r-spatial-and-time-accuracy) · [C21 model](argesim_benchmarks/models/c21_state_events.py)

## Independent numerical and statistical references

For C01 the weighted balance is $d(3r+2m+f)/dt=p-l_f f$. Compare all three components at every stored RK45 time for the five Task B loss rates with an independent Radau transcription. The maximum absolute tolerances are `2e-6` across a trajectory and `2e-7` at 10 s. The middle rate is the default Task A. Task C uses the two published Dymola equilibria. The timing script separately gates each method against a tighter RK45 endpoint. [C01 results](docs/C01_RESULTS.md)

For a stochastic result, specify the seed policy, number of independent runs, time window, summary statistic and reference uncertainty. C06 uses rounded published daily means. C16 compares independent samples of 50 week-260 restaurant counts and combines the two variances for each test. C17R's spatial result compares a seeded ensemble against a single published statistic. For C20, pooling individual orders and summarizing per-run medians answer different questions. [Reference comparisons](docs/PUBLISHED_REFERENCE_CHECKS.md) · [C20 experiment](docs/ARGESIM_CLOSURE_20261120.md)

For CP2's rope comparison the corrected reference uses `nu=0.06`, 500 spatial intervals, `dt=0.01` and a 0–10 s horizon. The implicit tridiagonal scheme is compared with a Fourier solution. The printed `nu=0.6` variant remains selectable. The cavity check uses the archived full-way D2Q9 implementation. [CP2 model](argesim_benchmarks/models/cp2_parallel_and_distributed.py) · [CP2 tests](tests/test_argesim_cp2.py)

## Discrete-event ordering and the NSA-DEVS experiments

`HyperTime` represents rational macro time and an integer microstep. `DesScheduler` orders pending callbacks by macro time, microstep, integer priority (lower first), then FIFO insertion order. Zero-delay relative scheduling advances the microstep. A finite horizon includes all microsteps at its macro time. Cancellation consumes no event budget. A callback can enqueue later work at its current time, so the model must define any simultaneous-event policy among pending callbacks. [Scheduler](nsa_devs/scheduler.py) · [Exact-time and priority tests](tests/test_des_scheduler.py)

The finite relay experiment compares final payload, event count and trace checksum before timing typed and raw-tuple implementations. The unit tests independently check the macro time and microstep sequence. Both timed paths perform one heap pop and payload update per component and one push per nonterminal component. The typed path retains event records and computes the checksum from the trace. The tuple path accumulates the checksum directly. The reported ratio includes both representation and trace handling. A separate Euler experiment reports the finite error of $(1-1/n)^n$ against $e^{-1}$. [Relay benchmark](benchmarks/benchmark_event_chain.py) · [Relay tests](tests/test_relay_chain.py)

```sh
python benchmarks/benchmark_event_chain.py --length 1000 --repeat 21
python benchmarks/benchmark_euler_convergence.py
```
