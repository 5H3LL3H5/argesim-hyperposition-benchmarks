# QSS and LIQSS solver guide

The repository contains independent, dependency-free reference backends for
the following ODE methods:

| Runtime name | Quantized polynomial | Intended use |
|---|---:|---|
| `qss1` | constant | first-order asynchronous baseline |
| `qss2` | linear | second-order black-box QSS |
| `qss3` | quadratic | smooth problems with fewer events |
| `qss4` | cubic | smooth problems where fourth-order event sections help |
| `cqss` / `cqss1` | centered constant | suitable Hamiltonian systems; published order one only |
| `liqss` / `liqss1` | constant | stiffness dominated by Jacobian diagonal entries |
| `liqss2` | linear | second-order linearly implicit QSS |
| `liqss3` | quadratic | third-order linearly implicit QSS |
| `eliqss` / `eliqss1` | constant | extended first-order LIQSS; identical to CheQSS1 |
| `eliqss2` | linear | extended second-order full-boundary update |
| `eliqss3` | quadratic | extended third-order full-boundary update |
| `cheqss` / `cheqss1` | constant | first-order Chebyshev LIQSS; identical to eLIQSS1 |
| `cheqss2` | linear | second-order minimax difference polynomial |
| `cheqss3` | quadratic | third-order minimax difference polynomial |
| `mliqss` / `mliqss1` | constant | mutually coupled stiff state pairs |
| `mliqss2` | linear | second-order coupled implicit update |
| `mliqss3` | quadratic | third-order coupled implicit update |
| `liqss-bdf` | LIQSS2 plus BDF1/2 | mixed state/time discretization with an explicit partition |

All quantized methods use `quantum`, scalar or one value per state.
`max_events` and `simultaneous_tolerance` have the same meaning across the
family. QSS3/QSS4 and the implicit variants also accept an absolute
`derivative_step` override for their right-hand-side Taylor stencil.

## Jacobian contract

LIQSS, eLIQSS, CheQSS and mLIQSS accept

```python
jacobian(time, state) -> square numeric matrix
```

If it is omitted, the solver constructs a dense centered finite-difference
Jacobian. `jacobian_step` is the positive relative perturbation used by that
fallback. mLIQSS also accepts `coupling_tolerance`, a non-negative threshold
relative to each Jacobian row scale that suppresses numerical-noise couplings.

```python
from argesim_benchmarks import InitialValueProblem, mliqss2

problem = InitialValueProblem(
    lambda _t, x: (-x[0] - x[1] + 0.2, x[0] - x[1] + 1.2),
    0.0,
    (-4.0, 4.0),
    20.0,
    autonomous=True,
)

result = mliqss2(
    problem,
    quantum=0.2,
    jacobian=lambda _t, _x: ((-1.0, -1.0), (1.0, -1.0)),
)
```

The dispatcher accepts the same methods. `eqss`, `eqss1`, `eqss2` and `eqss3`
are compatibility spellings for the canonical `eliqss*` names used by the
paper. `liqss_bdf` and `liqssbdf` normalize to `liqss-bdf`. When a model
already supplies only a `qss2` default quantum, CQSS, QSS3/QSS4 and every
LIQSS family inherit that quantum; an explicit method-specific default or user
option still wins.

## Numerical definition

Polynomial coefficients are stored in Taylor form around the current event.
QSS3 and QSS4 estimate the Taylor coefficients of `f(q(t))` with a symmetric
polynomial stencil, integrate that polynomial once, and find the first exact
real root of `x_i(t) - q_i(t) = +/- quantum_i`. Root isolation recursively
partitions the interval at derivative roots, so tangential roots are retained.

LIQSS1/2/3 implement the local scalar model

```text
x_i' = A_ii q_i + v_i(t)
```

and select either a future quantized polynomial or the local zero-derivative
polynomial. mLIQSS detects a mutually significant pair `(i, j)`. For order
`N`, it solves one bounded `2N x 2N` linear system so that both quantized
polynomials match the corresponding future state value and its first `N-1`
derivatives. This reproduces the published backward-Euler condition for
mLIQSS1 and the published value/slope conditions for mLIQSS2.

mLIQSS3 is clearly marked as a generalized third-order implementation: the
same future-matching construction is extended to value, slope and curvature.
The CIFASIS engine ships an mLIQSS3 backend, but the cited mLIQSS publication
formally derives only orders one and two. Tests therefore validate this
implementation by convergence and coupled-stiff-system behavior rather than
claiming line-by-line equivalence with that engine.

eLIQSS and CheQSS use the generalized difference polynomial
`p_i(t) = x_i(t) - q_i(t)`. eLIQSS retains the LIQSS polynomial but uses the
full bounded interval; CheQSS uses shifted Chebyshev polynomials. Their planned
self-event is kept distinct from a guard event caused by another quantized
state changing. This prevents harmless interior Chebyshev tangencies from
becoming artificial events.

## Centered QSS

CQSS1 implements the defining centered, memoryless quantizer

```text
q_i = (floor(x_i / quantum_i) + 1/2) * quantum_i
```

and keeps the continuous state on its piecewise-linear trajectory when a cell
boundary is crossed. The published geometric result is specialized to
suitable Hamiltonian systems; `cqss1` is therefore exposed explicitly rather
than advertised as a general QSS replacement. Its lack of hysteresis is part
of the method. An exact zero-time cell cycle raises `IntegrationError` instead
of silently consuming `max_events`. The defining publication specifies order
one only, so this repository does not invent `cqss2` or `cqss3` contracts.

## LIQSS-BDF mixed mode

`liqss_bdf(problem, quantum, bdf_partition=...)` implements the published
state/time split. Indices in `bdf_partition` use backward Euler for the first
accepted macro step and variable-step BDF2 thereafter. The complement keeps a
persistent LIQSS2 quantizer state. A linear interface polynomial and fixed
point iteration couple both sides; rejected BDF trials do not mutate the
accepted LIQSS state.

```python
from argesim_benchmarks import InitialValueProblem, liqss_bdf

problem = InitialValueProblem(
    lambda _t, x: (-x[0] + x[1], -10.0 * x[1]),
    0.0,
    (0.0, 1.0),
    1.0,
    autonomous=True,
)

result = liqss_bdf(
    problem,
    quantum=(5.0e-4, 1.0e-6),
    bdf_partition=(1,),
    jacobian=lambda _t, _x: ((-1.0, 1.0), (0.0, -10.0)),
)
```

With `bdf_partition=None`, every state uses BDF. That is the only deterministic
automatic choice available to a plain IVP with no event/dependency metadata,
and it also permits a non-autonomous right-hand side. A partial partition
requires `problem.autonomous=True`; known external switches belong in explicit
segments. The implementation uses its own dense BDF1/2 reference backend,
not CVODE. `rtol`, scalar/vector `atol`, step bounds, Newton controls and
interface-iteration controls are all validated dispatcher options.

## CIFASIS engine assessment

[`CIFASIS/qss-solver`](https://github.com/CIFASIS/qss-solver/tree/qss-solver-dev)
is useful as a standalone production engine and as an independent behavioral
oracle. It includes generated model callbacks, dependency graphs, schedulers,
event handlers and native QSS/LIQSS quantizers. It is not a drop-in replacement
for this repository's Python `rhs(time, state)` contract: embedding its core
would also require its generated-model ABI and a substantial native toolchain.

The CIFASIS project is distributed under
[`GPL-3.0-or-later`](https://github.com/CIFASIS/qss-solver/blob/qss-solver-dev/LICENSE).
No CIFASIS source is copied or linked here. The implementation in this
repository was derived from the published numerical definitions and retains a
separate Python architecture. A future optional subprocess adapter can remain
an explicit integration boundary if cross-engine validation is needed.

Primary algorithm references:

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

See [QSS_STATE_OF_THE_ART.md](QSS_STATE_OF_THE_ART.md) for the dated variant
matrix, architecture separation, implementation status and work comparison.

## Limits

- Quantized partitions require `problem.autonomous=True`. Known input changes
  must be represented as autonomous segments. A full BDF partition is the
  exception and supports a non-autonomous right-hand side directly.
- A smooth right-hand side is required for orders greater than one. Hybrid
  discontinuities belong in the repository's event/reset layer.
- The implementation deliberately recomputes dense derivatives after each
  event. It is a portable reference backend, not a sparse code-generated
  replacement for a production engine.
- LIQSS solves stiff ODEs. It does not solve algebraic constraints or provide a
  general-purpose DAE integrator.
- CQSS's conservation guarantees are not claimed outside the Hamiltonian class
  of its defining paper.
