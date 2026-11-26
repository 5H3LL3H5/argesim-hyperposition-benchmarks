# QSS and LIQSS solver guide

The [DEVS history](docs/QSS_DEVS_HISTORY.md) connects state quantization to discrete-event simulation. Its [RK comparison](docs/QSS_DEVS_HISTORY.md#two-embedded-rk-pairs-for-comparison) explains the explicit and stiff 3(2) alternatives.

## How to read a QSS method name

A Quantized State System (QSS) solver keeps two descriptions of each state. For a tank, `x` is the continuously estimated water level and `q` is the level supplied to the flow equation. With QSS1, `q` stays fixed while `x` rises or falls. A change of one quantum triggers an update. A second tank can update at a different time. Higher orders let `q` follow a slope or a curve between updates. A physical event, such as a ball striking the floor, has its own guard and reset. The quantum controls the local state approximation. Accuracy of a predicted impact time needs a separate check.

### Explicit and centered methods

| Runtime name | What the method does | Where the distinction matters |
|---|---|---|
| `qss1` | Holds each quantized value constant and advances the continuous state along a straight line. | A tank filling at a constant rate still triggers an update for each quantum of rise. |
| `qss2` | Carries a value and a slope in the quantized state. A directional derivative estimate gives the continuous path its curvature. | A constant-velocity flight segment can reach the next contact without an intervening quantizer update, as in C12. |
| `qss3` | Fits a quadratic quantized path and integrates a cubic continuous path. It predicts the next update from the first quantum-boundary root. | A smooth flight can span both ascent and descent in one step. C21 tests that the guard still finds the return to the floor. |
| `qss4` | Adds a cubic term to the quantized path and a fourth-degree term to the continuous path. | Each update needs more derivative information. Smooth sections can repay that cost, while frequent resets shorten them. |
| `cqss1` / `cqss` | Supplies the centre of the cell containing the continuous state. Crossing a cell edge selects the adjacent centre immediately. | This memoryless rule has geometric applications to suitable Hamiltonian systems. Repeated reversals at an edge can cause a zero-time cycle. |

### Logarithmic quantization on QSS1 and QSS2

With a state that falls from 100 to 0.03, a fixed absolute quantum fine enough for the tail can be expensive near the peak. Set `relative_quantum` to a non-negative fraction (scalar or one per state). At each of its own updates the component sets its new width to the larger of `quantum[i]` and `relative_quantum[i] * abs(x[i])`. The width stays fixed until that component updates again. Zero selects a fixed width for that component. The `qss1-log` and `qss2-log` labels in the CSV mean this option on the ordinary public functions.

```python
from argesim_benchmarks import InitialValueProblem, solve_ivp

decay = InitialValueProblem(lambda t, x: (-x[0],), 0, (100,), 8, autonomous=True)
log_result = solve_ivp(decay, "qss2", options={"quantum": 0.001, "relative_quantum": 0.001})
```

### Methods for stiff feedback

In a stiff system a fast relaxation can force many small updates while the observable of interest changes slowly. LIQSS estimates how each state's derivative changes with its own value, using the diagonal of the Jacobian. The modified family (mLIQSS) can also update a pair of states together when they feed back strongly on one another.

| Runtime name | What changes at an update |
|---|---|
| `bqss1` / `bqss` | Backward QSS chooses a nearby grid value ahead of the moving component. A component waits when its computed slope points away from its target. Try it for fast relaxation toward a slowly changing equilibrium, and check for event-time bias as you refine the quantum. It requires no Jacobian. |
| `liqss1` / `liqss` | Chooses a constant quantized value using local feedback. If the scalar equilibrium lies within the quantum band, the fast component can settle there until its forcing changes. |
| `liqss2` | Chooses both value and slope using diagonal feedback. The straight quantized path can track a drifting equilibrium. |
| `liqss3` | Adds curvature to the quantized path so that the local feedback model can follow smoothly changing forcing over a longer section. |
| `mliqss1` / `mliqss` | For a selected pair, solves for two constant quantized values together. Each value accounts for the other state's effect at a common future time. |
| `mliqss2` | Matches future values and slopes for a selected pair. Its four unknowns describe two straight quantized paths. |
| `mliqss3` | Also matches both curvatures, giving six unknowns for a selected pair. This third-order construction is an experimental repository extension of the published first- and second-order methods. |

### Methods that shape the quantization error

The difference `x − q` can vary across a smooth section while staying inside its local error band. Extended LIQSS (eLIQSS) uses the full predicted interval allowed by its difference polynomial. CheQSS chooses a shifted Chebyshev polynomial to distribute the error across that interval. A change in another component can invalidate either prediction early.

| Runtime name | What changes at an update |
|---|---|
| `eliqss1` / `eliqss` | Selects a constant quantized value and allows the linear difference to travel across the band before the next scheduled update. |
| `eliqss2` | Selects a straight quantized path. Its quadratic difference can reach zero inside the section and return to the boundary at the scheduled update. |
| `eliqss3` | Selects a quadratic quantized path. Its cubic difference can cross zero inside the section and reach the opposite boundary at the end. |
| `cheqss1` / `cheqss` | The first-degree Chebyshev difference gives the same constant quantized value and update time as eLIQSS1. The study lists both runtime names. |
| `cheqss2` | Uses a quadratic Chebyshev difference with a straight quantized path. The error can touch a bound inside the section and turn back without triggering an update. |
| `cheqss3` | Uses a cubic Chebyshev difference with a quadratic quantized path. Two interior extrema distribute the local error before the planned update. |

### Mixed state and time stepping

**`liqss-bdf`** splits the equations by state index. LIQSS2 advances one group asynchronously. The other takes implicit time steps, starting with backward Euler and continuing with variable-step BDF2. The two groups exchange predicted values and slopes and iterate to agree at their interface. This is useful when a known stiff subsystem can be assigned to the BDF group. With every state in that group the solver also accepts time-dependent inputs. [Partition options and example](#liqss-bdf-mixed-mode)

### Classical and DAE comparisons

| Entry point | How it advances the model |
|---|---|
| `euler` | Uses the slope at the start of each fixed time step for all states. The caller chooses a positive step small enough for the dynamics. |
| `rk4` | Combines four slope evaluations per fixed step. On smooth sections this gives fourth-order accuracy. The caller sets the step size. |
| `rk45` | Uses two Dormand–Prince approximations from shared stages to estimate error, reject a step if needed and choose the next step size. |
| `solve_dae` (IDAS) | Accepts a residual linking states, derivatives and algebraic unknowns. Starting from consistent values, IDAS uses implicit BDF steps to satisfy the equations together. The study uses this optional API separately on the regular index-one C21 diode model. |

## Options and interfaces

Pass an autonomous `InitialValueProblem` directly to a quantized method or select its runtime name through `solve_ivp`. The functions can be used independently of the benchmark runner. [Dispatcher and accepted options](argesim_benchmarks/runtime.py)

All quantized methods use `quantum`, scalar or one value per state.
`max_events` limits quantized updates and `simultaneous_tolerance` controls grouping of nearly simultaneous events. LIQSS-BDF also has a `max_steps` budget for its time-stepped partition. QSS3/QSS4 and the implicit variants also accept an absolute
`derivative_step` override for their right-hand-side Taylor stencil.
The quantizer accumulates elapsed time from the start of each solve.
Result timestamps, RHS evaluations, Jacobians and hybrid guards use the problem's absolute clock. The time-origin regressions compare work counts and state values for the same autonomous problem at zero and at a large offset. [Clock tests](tests/test_runtime.py)

The [selection study](docs/SOLVER_SELECTION.md) compares stiff and nonstiff cases at matched output tolerances and measures implicit Radau and BDF. The [earlier eight-case comparison](docs/SOLVER_COMPARISON.md) reports the original 456 configurations. The [methods appendix](docs/SOLVER_METHODS.md) also describes the optional residual-form IDAS interface.

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

## Reproducing a high-order boundary contact

The calendar operates on the polynomial represented by its input coefficients. A small residual at an extremum triggers root counting for ambiguous contacts. It does not establish a root. If the physical coefficients are uncertain, evaluate that uncertainty separately from the time tolerance. The three variants of the parabola and the rounded cubic in the regression suite distinguish the two questions.

[Illustrated derivation](docs/lehrbuch/gesamtausgabe/kapitel/06.md#qss-kontakt-nachweis) · [Registry of implementations, tests and figures](docs/lehrbuch/gesamtausgabe/rechenlabor/qss_pruefung/messung/kontakt_v919/methodenregister.csv)
