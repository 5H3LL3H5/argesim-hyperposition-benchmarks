# NSA-DEVS reference benchmarks

This repository contains a small, reproducible benchmark and correctness suite
for restricted NSA-DEVS timing semantics.

The repository name is historical. The active suite does not claim to
implement the official ARGESIM C01-C21 or CP1/CP2 benchmark definitions.

## What is implemented

- exact rational macro time plus an integer infinitesimal microstep;
- lexicographic ordering of values representing `a + b epsilon`;
- a finite acyclic Mealy-style relay chain;
- analytical trace checks;
- a workload-equivalent raw-tuple baseline;
- a finite convergence experiment for the NSA identity
  `st((1 - 1/N)^N) = exp(-1)`.

## What was removed

The former suite compared real computations against `sleep()` calls, no-op
functions or prescribed constants. Those programs could not support claims
about solver accuracy, rollbacks, SIMD utilisation or speedup and are absent
from the active tree.

## Run the tests

No third-party Python dependencies are required.

```bash
python -m unittest discover -s tests -v
```

## Run the experiments

```bash
python benchmarks/benchmark_event_chain.py --length 1000 --repeat 21
python benchmarks/benchmark_euler_convergence.py
```

The event-chain benchmark validates result parity before recording timing. It
reports median and interquartile range; it does not promise that the typed
representation is faster than the raw tuple.

## Interpretation

`HyperTime` is an executable encoding of the restricted ordering needed by the
reference model. It is not a complete hyperreal-number implementation. A
finite convergence table illustrates a standard NSA argument but does not
compute an infinite hyperinteger on the CPU.

