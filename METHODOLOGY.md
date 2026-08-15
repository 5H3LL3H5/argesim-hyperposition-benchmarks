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

- use `time.perf_counter_ns()`;
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
because they can execute with a very small step. QSS2 now has an actual
piecewise-linear quantizer, scaled directional derivative approximation and
convergence/fast-nonlinearity regression tests. LIQSS remains unimplemented.

Continuous benchmark wrappers use one strict dispatcher while Euler, RK4,
RK45, QSS1 and QSS2 remain separate algorithms. Unknown option names are
errors. Piecewise inputs are represented as contiguous autonomous segments for
QSS; a non-autonomous problem is never mislabeled autonomous merely to make a
backend accept it.

Hybrid models use one event layer for both classical and quantized continuous
modes. Every event declares a guard, direction, reset and target mode. The
runtime localizes a crossing, records its standard time plus a microstep, then
continues from the post-event state. A maximum-event guard turns Zeno behavior
into an explicit failure or a model-defined resting mode.

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

provides a structural equation check. Task-A timing is allowed only after the
endpoint agrees with a tighter, independently configured RK45 run within a
method-specific threshold. The tight RK45 result is a numerical oracle, not a
published reference solution; consequently C01 remains below the `validated`
gate until cross-tool or published reference trajectories are archived.
