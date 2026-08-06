# Benchmark methodology

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
- compliance with official ARGESIM benchmark definitions.

