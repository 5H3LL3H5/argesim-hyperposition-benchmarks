# Solver delta review: RK45, 2026-09-28

Base: `5b7022af3eea47b645c9624eb32590c09c7db6c9` (PR #56).
All tracked file contents in the isolated local snapshot were checked against
GitHub tree `17af2a7eaf2968c68d80ca13df168c2548658497` before editing.
The local Git history is a synthetic snapshot, not upstream history.

## Scope and findings

The existing runtime already dispatches Euler, RK4, RK45, QSS1–4, CQSS1,
LIQSS/eLIQSS/CheQSS/mLIQSS1–3 and LIQSS-BDF. This bounded extension concerns
RK45 and its dispatcher contract; it does not requalify the quantized methods.

| Finding | Delta | Regression evidence |
|---|---|---|
| A final remainder below `min_step` fails even if accurate | Permit a clipped final interval; continue enforcing error acceptance and reject an inaccurate sub-minimum retry | Non-divisible interval, tiny whole interval, inaccurate tiny interval |
| One absolute tolerance cannot express differently scaled state components | Accept a positive finite scalar or sequence of exactly the state dimension | Two-scale analytic decay through the dispatcher, scalar/vector parity, malformed input before RHS evaluation |
| Seven RHS evaluations on every trial duplicate the start derivative | FSAL caches accepted `k7`; rejected trials retain the original `k1` | Count actual calls on non-autonomous forced decay with rejected trials and repeated invocations |
| Squaring finite normalized errors can overflow | Compute RMS using scaled `math.hypot` | Finite normalized components of magnitude `1e200` |

The initial proposal is clipped into the configured step bounds before the
final-interval clip. A rejected interior step below `min_step` still fails.
The RHS must return the same derivative for the same time and state. Hidden
mutable input switches require explicit integration segments; the cache does
not survive calls. User exceptions and invalid derivatives remain errors.

For A accepted steps and R rejected trials, completed integrations now perform
`1 + 6 * (A + R)` RHS evaluations, versus the previous `7 * (A + R)`.
This is an operation-count improvement, not a measured wall-time speedup.
Scalar tolerances retain their contract; the more stable norm can cause
roundoff-level differences in adaptive time grids.

## Numerical references

- Dormand and Prince, *A family of embedded Runge-Kutta formulae*, 1980,
  https://doi.org/10.1016/0771-050X(80)90013-3.
- SciPy's official [RK45 documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.RK45.html)
  documents the 5(4) pair and component-wise absolute error tolerances.
  This change adds no SciPy runtime dependency or copied implementation.

## Remaining solver milestones

1. Add an optional pinned CIFASIS subprocess oracle for selected smooth and
   stiff models; compare accuracy and event semantics before speed claims.
2. Qualify QSS variant convergence independently on analytic coupled systems;
   preserve the existing generalized-mLIQSS3 qualification caveat.
3. Extend reproducible work/accuracy sweeps using measured RHS/event counts,
   fixed parameters, solver options, provenance and checksummed artifacts.
4. Assess dense recomputation costs before changing QSS scheduling or adding
   sparsity metadata; such changes need their own focused correctness review.

Successful local execution does not promote any benchmark's scientific
evidence level. No claim of a complete fresh audit of every solver is made.

## Independent numerical spot checks

SciPy 1.17.0 `solve_ivp(method="DOP853", rtol=2.3e-14,
atol=RK45_atol*1e-4)` served as a separate numerical reference. RK45 used
`rtol=1e-9` and an initial step equal to the entire interval (forcing retries).
The metric is `max(abs(RK45_final - reference_final) / component_scale)`.
These are local diagnostic observations, not new scientific evidence gates.

| RHS | Initial state; interval | RK45 atol | Component scales | Maximum scaled endpoint difference |
|---|---|---|---|---:|
| `x'=-x` | `(1,)`; [0,10] | `(1e-12,)` | `(1,)` | 2.91e-13 |
| `x'=-x+sin(t)` | `(1,)`; [0,10] | `(1e-12,)` | `(1,)` | 1.24e-10 |
| `x'=v; v'=-x` | `(1,0)`; [0,20] | `(1e-12,1e-12)` | `(1,1)` | 2.12e-9 |
| `x'=-x; y'=-2y` | `(1e6,1e-6)`; [0,2] | `(1e-5,1e-15)` | `(1e6,1e-6)` | 2.42e-10 |

The oscillator's zero initial velocity is normalized by its unit amplitude,
not by its zero initial value. Analytic decay and forced-decay checks remain
in the dependency-free regression tests.
