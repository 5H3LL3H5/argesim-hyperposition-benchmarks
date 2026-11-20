# Benchmark methodology

## 0. Evidence gates

An official ARGESIM entry advances only through these ordered gates:

1. **cataloged** - official identity, active revision and model family checked;
2. **specified** - equations, parameters, events, stochastic assumptions,
   experiments and required outputs transcribed from the primary definition;
3. **implemented** - executable model and every required task present;
4. **validated** - independent analytical, tabulated or high-accuracy reference
   values pass declared tolerances;
5. **benchmark-ready** - workload parity, environment capture, warm-up,
   repetitions and raw result retention are complete.

A catalog entry or placeholder never counts as an implementation.

## 1. Research questions

1. Does the executable time encoding preserve the analytical order of a
   finite NSA-DEVS causal chain?
2. What overhead does the typed encoding introduce relative to a raw tuple
   with identical semantics and work?
3. Do finite Euler approximations converge toward the standard value predicted
   by the corresponding NSA identity?

## 2. Correctness before performance

Every timed implementation must return an observable result. Candidate and
baseline results are compared before any performance ratio is calculated.
For the relay experiment the observables are:

- final payload;
- number of processed components;
- macro-time projection;
- first and last microstep;
- deterministic checksum of the trace.

## 3. Workload equivalence

The typed and raw-tuple relay implementations both perform:

- one priority-queue pop per component;
- one payload transformation per component;
- one trace update per component;
- one priority-queue push for every non-terminal component.

The only intended difference is representation and dispatch overhead.

## 4. Timing protocol

- use the monotonic `time.perf_counter()`/`perf_counter_ns()` clock;
- perform untimed warm-up runs;
- record complete-run durations;
- use an odd repetition count of at least  nine for exploratory results;
- report median and interquartile range;
- retain individual durations in JSON output;
- never use `sleep()` as simulated work;
- never substitute an analytical answer for candidate computation.

For publication, record interpreter, OS, kernel, CPU, affinity and power
management settings. Use a dedicated benchmark framework if sub-microsecond
effects become relevant.

## 5. Accuracy protocol

The finite Euler experiment evaluates

\[
x_n=(1-1/n)^n
\]

against \(e^{-1}\). It reports finite absolute error. The phrase "standard
part" describes the non-standard limiting theorem; it is not used as a claim
of zero error in a finite program.

## 6. Prohibited inferences

These experiments do not establish:

- physical infinitesimal computation;
- superiority over a production DEVS simulator;
- absence of data races or locks;
- absence of Time Warp rollbacks;
- parallel speedup;
- benchmark readiness beyond the catalog's recorded evidence gate.

## 7. Solver comparisons

All solver candidates receive one immutable model definition, initial state,
time interval and output grid. Accuracy is checked before runtime is compared.
Adaptive and event-driven methods report accepted and rejected steps or events
and right-hand-side evaluations in addition to wall time.

Explicit methods are not presented as suitable stiff or DAE solvers merely
because they can execute with a very small step. QSS2 has an actual
piecewise-linear quantizer and scaled directional derivative approximation.
QSS3/QSS4 use polynomial quantizers and isolate every real event root through
degree four rather than sampling for a sign change. Their black-box right-hand
side Taylor coefficients use symmetric polynomial stencils.

LIQSS1/2/3 use a diagonal local linearization. mLIQSS1/2/3 additionally detect
mutually influential pairs and solve a bounded two-state linearly implicit
polynomial update. An exact model Jacobian may be supplied; the portable
fallback evaluates a dense centered finite-difference Jacobian. Tests cover
quantum convergence, a diagonal stiff system, pairwise stiff oscillation and
exact-versus-numerical Jacobian parity. These are ODE solvers, not DAE solvers.

CQSS1 uses the defining memoryless cell-center quantizer. Its Hamiltonian
conservation test is kept separate from general IVP convergence tests, and an
exact zero-time cell cycle is reported because the method intentionally has no
hysteresis. No unpublished higher-order centered CQSS contract is inferred
from similarly named experimental engine files.

LIQSS-BDF is evaluated as a mixed state/time method, not a renamed quantizer.
Tests cover the full-BDF stiff limit, tolerance convergence, a partitioned
triangular system, persistent LIQSS events and strict partition validation.
The implementation uses backward Euler startup and variable-step BDF2 rather
than claiming to embed the paper prototype's CVODE backend.

Continuous benchmark wrappers use one strict dispatcher while Euler, RK4,
RK45 and every QSS/LIQSS order remain separate algorithms. Unknown option
names are errors. Existing per-model QSS2 quanta are inherited by newer
quantized methods unless a method-specific default is supplied. Piecewise
inputs are represented as contiguous autonomous segments for QSS; a
non-autonomous problem is never mislabeled autonomous merely to make a backend
accept it.

Hybrid models use one event layer for both classical and quantized continuous
modes. Every event declares a guard, direction, reset and target mode. The
runtime localizes a classical crossing against cubic-Hermite dense state
output (or deliberately uses fixed-step endpoint semantics when localization
is disabled), records its standard time plus a microstep, then continues from
the post-event state. A maximum-event guard turns Zeno behavior into an
explicit failure or a model-defined resting mode.

Callback DES workloads share the deterministic `HyperTime` scheduler. A
finite horizon includes all microsteps at its terminal macro time; idle drains,
cancellation and maximum-event limits are part of the public contract.

## 8. PDE and learned-operator protocol

Time-dependent PDEs are spatially discretized first. Grid size, stencil,
boundary treatment and spatial error are reported separately from temporal
solver error. Neural-operator training cost, inference cost and data generation
cost are reported separately. Evaluation requires held-out data, PDE residual,
boundary-condition error and out-of-distribution tests.

## 9. ARGESIM C01 protocol

The C01 transcription is checked directly against the official definition:
state order, five rate parameters, production term, initial state and tasks
A-C are explicit in code. The weighted population balance

\[
\frac{d}{dt}(3r+2m+f)=p-l_f f
\]

provides a structural equation check. Before timing a Task A solver, compare its
endpoint with a tighter run of the repository's RK45 using the method-specific
threshold. For independent validation, integrate a separate transcription of
the equations with SciPy Radau. Compare the default RK45 trajectory at every
output time for each of the five Task B loss rates. The absolute tolerance is
`2e-6` for each component across the trajectory and `2e-7` at 10 s. The
middle loss rate also covers the default Task A trajectory. For Task C, check
both stationary states against the published Dymola values. The catalog's
`validated` status covers these numerical cases. Timing comparisons between
tools still require equivalent workloads. [C01 results](docs/C01_RESULTS.md)

## 10. Parallel and distributed workload protocol

CP1 and CP2 use `argesim_benchmarks.parallel.OrderedExecutor`. Worker pools are
constructed once and reused across time steps or Runge-Kutta stages. Serial and
parallel paths receive the same ordered input tuple and callable. Every timing
report retains all repeat samples and records the maximum result error before
calculating speedup and efficiency. A measured speedup below one is a valid
negative result, explicitly expected for the fine-grained CP1-B system.

Official full sizes remain defaults in workload entry points. CI uses smaller
parameter values to verify the same code path; it does not present reduced-run
timings as official benchmark results.

## 11. Completed-family reference protocol

- C05 checks the published event counts and switch times for the default and
  Task D cases. An independent high-precision calculation checks the decimal
  precision study. [Reference comparisons](docs/PUBLISHED_REFERENCE_CHECKS.md)
- C09 implements the stable `change-level` FIS signal shown in the published
  Simulink solution and retains the contradictory literal printed error
  difference as an explicit alternative. The qualitative reference behaviour
  is tested without inventing numeric curve samples.
- C16 compares the count of restaurants at week 260 across 50 replications
  with the published AnyLogic and Java OO statistics. Report the time average
  after week 260 separately. Use the sample and published variances to compute
  the standard error of each difference of means. [C16 comparison](docs/PUBLISHED_REFERENCE_CHECKS.md)
- C17R checks the CA population invariant and the published lattice/contact
  identification formula. Random seeds are local to each replication.
- C18 keeps data provenance in `C18DataSet`. Figure digitizations are not
  labelled as recovered measurements. Synthetic ARX recovery tests algorithmic
  correctness independently of those digitizations. Error trends and both
  teacher-forced and free-running ANN predictions are retained separately.
- C20 uses at least ten replications for official summary calls and reports
  median, first/third quartiles and IQR. Reduced CI calls test scenario logic,
  not performance or production statistics.
- C21 checks published event-contact limits, pendulum stop/kick outputs and
  dynamic-contact samples as well as the RLC algebraic residual for DAE,
  interpolated and explicit index-reduced forms. Agreement does not imply a
  general-purpose DAE solver.
- CP2 uses the peer-reviewed correction `nu=0.06`, 500 spatial intervals,
  `dt=0.01` and a 0-10 s horizon. Its implicit tridiagonal rope scheme is
  checked against the independent Fourier series. The printed `nu=0.6`
  variant remains explicit for provenance. LBM collision/streaming follows the
  archived full-way bounce-back MATLAB implementation, including imposed lid
  velocity in the reported output field.
