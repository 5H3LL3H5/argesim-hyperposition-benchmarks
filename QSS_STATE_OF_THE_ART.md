# QSS numerical methods and implementation status

The numerical methods below are compared with their cited publications.
The implementation column and event counts describe the Python backends in
this repository. For accepted option names and runnable examples, see the
[solver guide](QSS_SOLVERS.md).

## Numerical families

| Family | Orders | Main purpose | Status in this repository |
|---|---:|---|---|
| QSS | 1-3 | explicit asynchronous integration | implemented |
| QSS4 | 4 | higher-order smooth polynomial sections | implemented as a reference extension |
| BQSS | 1 | historical backward/stiff QSS precursor | documented; superseded by LIQSS |
| LIQSS | 1-3 | stiffness dominated by the Jacobian diagonal | implemented |
| mLIQSS | 1-2 | mutually coupled stiff state pairs | implemented |
| mLIQSS3 | 3 | engine-level higher-order pair extension | implemented, explicitly experimental |
| eLIQSS / EQSS | 1-3 | extended update policy with larger bounded segments | implemented |
| CheQSS | 1-3 | Chebyshev minimax difference polynomial | implemented |
| CQSS | 1 in the defining publication | geometric integration of suitable Hamiltonian systems | implemented with explicit no-hysteresis cycle detection |
| LIQSS-BDF | LIQSS2 + BDF | mixed state/time discretization | implemented with persistent LIQSS2 and an independent BDF1/2 backend |

The generalized LIQSS construction is described in the 2026 publication
[On General Linearly Implicit Quantized State System Methods](https://doi.org/10.1007/s40314-026-03858-3).
It defines `eLIQSS1`-`eLIQSS3` and `CheQSS1`-`CheQSS3`. The former retains the
LIQSS difference polynomial but waits until the full error boundary is reached;
the latter selects a shifted Chebyshev polynomial and maximizes the locally
admissible segment under the paper's assumptions. Both keep
`abs(x_i - q_i) <= quantum_i` in the local model. CheQSS1 and eLIQSS1 are
mathematically identical.

These methods are exposed under canonical runtime names `eliqss1` through
`eliqss3` and `cheqss1` through `cheqss3`. `eliqss`, `cheqss` and the CIFASIS
spellings `eqss`, `eqss1`, `eqss2`, `eqss3` normalize to those canonical
implementations; they are compatibility spellings, not duplicate algorithms.

CQSS is a different specialization. Its defining publication constructs a
memoryless centered quantizer for Hamiltonian systems and notes both its useful
geometric properties and its lack of hysteresis, which can cause infinitely
fast oscillation on general systems. The runtime exposes the published
first-order method as `cqss` / `cqss1`, detects exact zero-time cell cycles and
does not pretend that the domain-specific method is a safe general replacement
for QSS/LIQSS. Experimental CIFASIS methods bearing `CQSS1`-`CQSS3` names are
not treated as published higher-order centered-quantizer contracts here.

LIQSS-BDF is not a new scalar quantizer. The defining mixed-mode paper splits
the state into an LIQSS2 partition and a classical BDF partition, exchanging
order-compatible interface polynomials at classic time steps. The reference
backend here preserves LIQSS2 quantizer polynomials across accepted BDF macro
steps, uses linear waveform relaxation at the interface and advances the time
partition with backward Euler followed by variable-step BDF2. The paper's
prototype uses LIQSS2 plus CVODE-BDF; this implementation deliberately uses an
independent dense Python BDF backend and makes no CVODE equivalence claim.

## Implementation details

The generalized solver implements the published difference-polynomial model

```text
p_i(t) = x_i(t) - q_i(t)
x_i'   = a_i q_i + u_i(t),  a_i = partial f_i / partial x_i
```

independently in Python. It computes the order-specific positive segment root,
constructs the complete quantized Taylor section and schedules its intended
self-event. A separate `1.001 * quantum` guard detects invalidation caused by a
different state changing first. This distinction matters for CheQSS: internal
Chebyshev extrema may touch the error boundary without leaving the admissible
interval and must not be counted as self-events.

The Jacobian callback and dense centered finite-difference fallback have the
same contract as LIQSS/mLIQSS. The polynomial root finder partitions at derivative roots and uses numerical
tolerances to detect repeated roots. The native CIFASIS pilot exercises QSS1
and QSS2 for scalar decay. The generalized methods in the comparison below
use the Python implementations. [Root isolation](argesim_benchmarks/solvers/_polynomial.py) ·
[Native pilot](docs/CIFASIS_ORACLE.md)

## Reproducible work comparison

From the repository root run the scalar work comparison.

```bash
python benchmarks/benchmark_qss_variants.py --repeat 9 --warmup 1
```

For `x' = 1 - x`, `x(0) = 0`, `t_final = 5` and `quantum = 0.01`, the
deterministic accepted-event counts are:

| Order | LIQSS | eLIQSS | CheQSS |
|---:|---:|---:|---:|
| 1 | 98 | 49 | 49 |
| 2 | 11 | 6 | 4 |
| 3 | 9 | 3 | 2 |

The benchmark refuses to report timings unless every endpoint remains within
`2.1 * quantum` of the analytic solution. These counts validate this Python
implementation's event policy; they are not presented as a reproduction of C
runtime measurements from the paper.

`python benchmarks/benchmark_cqss_liqss_bdf.py --repeat 9 --warmup 1`
separately gates CQSS1 by the harmonic-oscillator energy span and the mixed
LIQSS2-BDF solver by the exact endpoint of a partitioned triangular system.
This separation avoids applying CQSS outside the Hamiltonian problem class for
which it was defined.

## Policies and execution architectures

| Layer | State of practice | Repository boundary |
|---|---|---|
| Error policy | absolute plus state-relative logarithmic quantum | fixed positive scalar/vector quantum; relative policy remains separate work |
| Dependency handling | generated incidence matrices and sparse affected-state updates | dense recomputation after every event for reference clarity |
| Execution | DEVS atomic models or a stand-alone priority scheduler | deterministic stand-alone Python event loop |
| Hybrid behavior | zero crossings, external events and local resets | provided by the separate reusable hybrid runtime |
| Mixed state/time | LIQSS2 partition coordinated with CVODE-BDF | persistent LIQSS2 plus independent BDF1/2, selected by `bdf_partition` |
| Parallelism | partitioned/shared/distributed schedulers in production research engines | serial QSS event loops and separate ordered thread/process utilities for benchmark workloads |
| Model frontend | symbolic/code-generated Modelica subset in CIFASIS | explicit Python `rhs(time, state)` and optional Jacobian |

The structural gap is deliberate. Sparse code generation can dominate runtime
on large systems, while the dense backend here is easier to audit and compare
against ARGESIM reference models. Solver method, hybrid/event semantics and
execution policy remain separate reusable layers.

## Primary sources

- E. Kofman and S. Junco, [Quantized-State Systems: A DEVS Approach for
  Continuous System Simulation](https://www.fceia.unr.edu.ar/~kofman/files/qss.pdf).
- G. Migoni et al., [Linearly implicit quantization-based integration methods
  for stiff ordinary differential equations](https://people.inf.ethz.ch/cellier/Pubs/Sim/simpat_13b.pdf).
- F. Di Pietro et al., [Improving Linearly Implicit Quantized State System
  Methods](https://www.fceia.unr.edu.ar/~kofman/files/liqss_imp_v2.pdf).
- M. Bergonzi et al., [On General Linearly Implicit Quantized State System
  Methods](https://doi.org/10.1007/s40314-026-03858-3) (2026).
- M. Bortolotto et al., [Integration by Quantization in Hamiltonian Systems
  (CQSS)](https://usuarios.fceia.unr.edu.ar/~kofman/files/CQSS.pdf).
- M. Di Pietro et al., [Mixed-Mode State-Time Discretization in ODE Numerical
  Integration](https://fceia.unr.edu.ar/~kofman/files/mixed_mode_v5.pdf).
- [CIFASIS Stand-Alone QSS Solver](https://github.com/CIFASIS/qss-solver/tree/qss-solver-dev)
  and its [GPL-3.0-or-later license](https://github.com/CIFASIS/qss-solver/blob/qss-solver-dev/LICENSE).
