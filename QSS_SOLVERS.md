# QSS and LIQSS solver guide

The single dispatcher exposes Euler, RK4 and adaptive RK45 for explicit
ODEs. Euler and RK4 take a positive fixed `step`. RK45 accepts relative
and component-wise absolute tolerances. For an autonomous system, the
following quantized methods are also available. The full BDF partition
accepts time-dependent inputs. [Dispatcher and accepted options](argesim_benchmarks/runtime.py)

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
`max_events` limits quantized updates and `simultaneous_tolerance` controls grouping of nearly simultaneous events. LIQSS-BDF also has a `max_steps` budget for its time-stepped partition. QSS3/QSS4 and the implicit variants also accept an absolute
`derivative_step` override for their right-hand-side Taylor stencil.
The quantizer accumulates elapsed time from the start of each solve.
Result timestamps, RHS evaluations, Jacobians and hybrid guards use the problem's absolute clock. The time-origin regressions compare work counts and state values for the same autonomous problem at zero and at a large offset. [Clock tests](tests/test_runtime.py)

## Jacobian contract

LIQSS, eLIQSS, CheQSS and mLIQSS accept a `jacobian(time, state)` callback returning a square matrix of numeric partial derivatives in state order.

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
has no method-specific defaults for a quantized backend, the dispatcher uses the model’s `qss2` defaults, or its `qss1` defaults if `qss2` is absent. Explicit user options take precedence.

## Numerical definition

Polynomial coefficients are stored in Taylor form around the current event.
QSS3 and QSS4 estimate the Taylor coefficients of `f(q(t))` with a symmetric
polynomial stencil, integrate that polynomial once, and numerically locate the first positive
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

With `bdf_partition=None`, every state uses BDF and the right-hand side can
depend explicitly on time. Any quantized partition requires
`problem.autonomous=True`. Use separate autonomous segments for known
switches. The reference backend implements dense BDF1/2 with Newton
iteration, adjustable step bounds, scalar/vector `atol` and relative
tolerance. [Mixed-mode solver](argesim_benchmarks/solvers/mixed_qss.py)

## CIFASIS engine assessment

The repository ships an optional subprocess adapter for the pinned CIFASIS
engine. It translates a scalar linear-decay request into micro-Modelica and
runs the native QSS1 or QSS2 method. The archived pilot checks the analytic
solution at every emitted sample and reports endpoint coverage separately.
The native pilot and the Python solver examples have different input
contracts. [Installation and protocol](docs/CIFASIS_ORACLE.md) ·
[Native results](docs/evidence/cifasis-linear-decay-20260928.json)

Primary algorithm references:

- G. Migoni et al., [Linearly implicit quantization-based integration methods
  for stiff ordinary differential equations](https://people.inf.ethz.ch/fcellier/Pubs/Sim/simpat_13b.pdf).
- F. Di Pietro et al., [Improving Linearly Implicit Quantized State System
  Methods](https://www.fceia.unr.edu.ar/~kofman/files/liqss_imp_v2.pdf).
- M. Bergonzi et al., [On General Linearly Implicit Quantized State System
  Methods](https://doi.org/10.1007/s40314-026-03858-3) (2026).
- M. Bortolotto et al., [Métodos de integración por cuantificación en sistemas
  hamiltonianos (CQSS)](https://usuarios.fceia.unr.edu.ar/~kofman/files/lsd0802.pdf).
- F. Di Pietro et al., [Mixed-Mode State-Time Discretization in ODE Numerical
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

## Classical adaptive baseline

`rk45` accepts a positive finite scalar `atol` or a list/tuple containing one
positive finite absolute tolerance per state component. `rtol` remains scalar.
The same options work through `solve_ivp`:

```python
from argesim_benchmarks import InitialValueProblem, solve_ivp

problem = InitialValueProblem(lambda t, x: (-x[0], t - x[1]), 0.0, (1.0, 0.0), 1.0)
result = solve_ivp(problem, "rk45", options={
    "rtol": 1e-8, "atol": (1e-6, 1e-12),
})
```

A clipped final step may be shorter than `min_step` and still undergoes local
error control. The initial proposal is clipped to the configured step bounds.
Dormand-Prince endpoint derivatives are reused (FSAL), including start-value
reuse on rejected trials. The RHS must be deterministic for each `(time, state)`;
known discontinuities belong in separate integration segments. Each solver
invocation starts with a fresh cache. See the
[bounded solver review](docs/SOLVER_REVIEW_2026-09-28.md) for regressions and limits.
