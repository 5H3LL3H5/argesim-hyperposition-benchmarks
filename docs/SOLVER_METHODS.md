# How the solvers advance a model

A solver choice starts with the equation supplied by the model. A right-hand side returns derivatives for known states. A DAE residual returns equation defects for a proposed state, derivative and algebraic variable. A discrete-event scheduler advances to the next queued event. These are different computational problems. The ARGESIM study measures 18 named quantized ODE configurations and three classical ODE methods. A separate circuit experiment exercises the residual DAE interface.

## Quantization, error and physical events

For an autonomous ODE the quantized solver evolves a continuous approximation `x` using the derivative evaluated at a quantized approximation `q`. Each component predicts when its polynomial difference `x_i - q_i` will reach a quantization boundary. The earliest prediction advances the simulation clock. Components due together can update at the same time. A slowly changing state can retain its polynomial while a fast state generates many updates. In this Python implementation derivative and Jacobian work can still be dense.

The quantum has the units of its state. A factor of 0.001 means 0.001 times each component's supplied scale. Tightening it generally increases work. The quantum controls a local approximation, while coupling, phase drift and resets determine the error of the final observable. Where a guard is nearly tangent, even a small state error can move a crossing appreciably. The study therefore checks crossing times and counts separately from state errors.

A quantizer update changes the numerical representation. A model event, such as hitting the floor, changes the physical equations or state. For a coordinate threshold, the hybrid runtime splits each accepted cubic Hermite interpolant at its coordinate extrema, brackets directed crossings and selects the earliest event. It then restarts with the model's reset. This covers leaving and returning to the same surface within one accepted step. Accuracy still depends on the interpolant. For opaque nonlinear guard functions, interior sampling has limited coverage. Supply a physically justified maximum segment span when several crossings can occur within one step. [Hybrid runtime and tests](../tests/test_hybrid_runtime.py)

## Explicit quantized methods

| Method | What happens at an update | Practical consequence |
|---|---|---|
| QSS1 | Holds the quantized value constant and integrates a constant derivative until a state reaches its boundary. | Small work per update. A fast transient or a long oscillation can require many updates. |
| QSS2 | Carries the quantized value and slope. A local derivative estimate gives a quadratic state trajectory. | Tracks a ramp with fewer updates. Changes of slope at physical switches still need a restart. |
| QSS3 | Uses a quadratic quantized path and a cubic continuous path. A Taylor stencil estimates derivative evolution and a polynomial root determines the next update. | Smooth curvature can be followed over a long interval. The C21 return to the floor can lie inside that interval. |
| QSS4 | Raises the quantized path to degree three and the continuous path to degree four. It estimates one more Taylor coefficient. | Extra evaluations can save events on smooth motion. Stencil accuracy, restarts and event localization can limit the benefit. |
| CQSS1 | Places each value at the centre of its current cell and changes cells at a boundary. There is no hysteresis. | Of particular interest for suitable Hamiltonian systems. A boundary cycle can occur on other equations. This implementation detects a zero-time cycle. |

The order describes the local construction of smooth sections. It does not predict a corresponding factor of improvement after a discontinuity. CQSS1's conservation result applies to the model class of its defining paper. Its inclusion on dissipative models in this study is an empirical stress test. [Centered quantization paper](https://usuarios.fceia.unr.edu.ar/~kofman/files/lsd0802.pdf)

## Linearly implicit methods

A stiff stable mode can make an explicit quantizer repeatedly reverse direction near equilibrium. LIQSS approximates the contribution of the current component by its diagonal Jacobian entry, treating the remaining forcing as a local polynomial. This allows the new quantized path to anticipate its own feedback. An analytic Jacobian saves dense finite differences where one is available. Off-diagonal coupling, changes of mode and a poor linear approximation can still dominate work or error. [LIQSS derivation](https://people.inf.ethz.ch/fcellier/Pubs/Sim/simpat_13b.pdf)

| Method | Local construction | What distinguishes this order |
|---|---|---|
| LIQSS1 | Implicit scalar update with a constant quantized state. | Can settle a fast diagonal mode at its local equilibrium. Slowly varying forcing generates fresh updates. |
| LIQSS2 | Linear quantized trajectory with diagonal feedback. | Carries the slope through a smooth transient. Changes in a neighbouring state can invalidate the prediction. |
| LIQSS3 | Quadratic quantized trajectory with the same diagonal approximation. | Represents curvature of the forcing. Its higher derivative work pays off only if the section lasts long enough. |
| eLIQSS1 | Uses the extended bounded difference with a constant quantized state. | At order one it gives the same construction as CheQSS1. The two runtime names are counted separately. |
| eLIQSS2 | Linear quantized trajectory with the extended boundary interval. | Uses more of the available error band than the corresponding LIQSS construction. |
| eLIQSS3 | Quadratic quantized trajectory with the extended boundary interval. | Carries curvature through the predicted self-event. A neighbour's update can shorten the interval. |
| CheQSS1 | Uses the first-order shifted Chebyshev difference construction. | Shares the eLIQSS1 polynomial. A timing difference between these names cannot establish algorithmic superiority. |
| CheQSS2 | Uses a shifted Chebyshev difference polynomial with a linear quantized trajectory. | Distributes the deviation across the interval. An interior touch of the error bound need not trigger a new event. |
| CheQSS3 | Applies the same minimax principle with a quadratic quantized path. | Distinguishes the planned self-event from an update forced by another state, preserving the intended error profile. |

In eLIQSS and CheQSS a scheduled self-event and a change in a neighbouring state have different meanings. The former completes a predicted approximation interval. The latter can change the local forcing before the prediction is due. [Generalized LIQSS construction](https://doi.org/10.1007/s40314-026-03858-3)

## Coupled and mixed methods

| Method | Equations advanced together | Cost and scope |
|---|---|---|
| mLIQSS1 | A mutually significant pair gets a bounded two-variable value update with a backward-Euler-type matching condition. | Can handle a stiff feedback loop that two independent diagonal updates represent poorly. Pair detection and a linear solve add work. |
| mLIQSS2 | Matches future values and slopes for two linear quantized paths. | Four coefficients are coupled. The additional conditions improve the local representation for smooth forcing. |
| mLIQSS3 | Extends the pair update to values, slopes and curvatures. | Six coefficients are coupled. This is the repository's higher-order generalization. The cited pair-method derivation covers orders one and two. |
| LIQSS-BDF | Advances the chosen stiff partition with backward Euler at startup and variable-step BDF2 thereafter. The complementary states retain LIQSS2 quantizers. | An interface polynomial and fixed-point iteration exchange information across partitions. Partition choice, rejected macro steps and coupling costs can dominate. |

The coupled methods use a relative threshold to identify significant reciprocal Jacobian entries. LIQSS-BDF instead asks the caller for the BDF state indices. With an empty partition the calculation reduces to the quantized side. With every state in the BDF partition it becomes time-stepped and supports explicit time dependence. In the study all mixed partitions contain states on both sides. [Coupled method](https://www.fceia.unr.edu.ar/~kofman/files/liqss_imp_v2.pdf) · [Mixed state/time method](https://fceia.unr.edu.ar/~kofman/files/mixed_mode_v5.pdf)

## Classical time stepping and numerical references

**Euler** advances every component by one fixed interval using the derivative at the start. Its first-order error and finite stability interval make a fixed step particularly consequential on C03 and C05. A step small enough for stability can exhaust the work budget.

**RK4** evaluates four stages across each fixed step and combines their slopes. On smooth ODEs it has fourth-order global accuracy under the usual regularity assumptions. It has no embedded error estimate. Changes in forcing are supplied as segment boundaries, and event crossings use the hybrid layer.

**RK45** uses the Dormand–Prince 5(4) pair. Two approximations from shared stages estimate local error and determine whether to accept the step. Absolute component tolerances define a floor near zero and the relative tolerance scales with the state. Endpoint derivative reuse saves evaluations. Local error control does not remove the stability constraint of an explicit method on a stiff model. [Classical implementations](../argesim_benchmarks/solvers/explicit.py)

The reference computations use different tools according to the observable. A matrix exponential propagates an affine linear phase, including its constant forcing via an augmented state. SciPy DOP853 supplies a high-accuracy explicit reference for smooth segments. SciPy Radau uses implicit collocation for a stiff reference. Both can quantify integration error with a shared right-hand side. A separately transcribed equation or an analytical event time also tests parts of the model formulation.

## IDAS for a residual-form DAE

The optional `solve_dae` API accepts equations of the form `F(t, x, xdot, z) = 0`. The caller supplies consistent initial values for the differential state, its derivative and the algebraic variables. The residual must be expressible with CasADi symbols. The implementation integrates `x` and solves for the augmented algebraic unknowns `(z, xdot)` using SUNDIALS IDAS through CasADi. The matrix of partial derivatives of the residual with respect to these unknowns must be nonsingular on the solution branch. The adapter checks it at the initial point.

IDAS uses a variable-order, variable-step BDF approach with nonlinear equation solves. Constraint accuracy depends on initialization, equation scaling and tolerances. The result includes the requested output times, differential states, algebraic states, derivatives and the largest absolute residual over those outputs. This sampled defect is sensitive to units. It is a different quantity from trajectory error against an independent solution. The adapter covers regular index-one systems. Higher-index mechanical constraints need index reduction or another formulation. The present interface provides output sampling. The diode comparison estimates its crossing times from bracketing outputs.

For example, take a decaying state constrained by `z = x²`. The initial derivative follows from the differential equation. The same entry point handles a multi-state implicit mass matrix or nonlinear derivatives when the regularity condition holds.

```python
from argesim_benchmarks import solve_dae

solution = solve_dae(
    lambda t, x, v, z: (v[0] + x[0], z[0] - x[0] ** 2),
    times=(0, 0.5, 1), x0=(1,), xdot0=(-1,), z0=(1,),
)
```

Install with `python -m pip install '.[dae]'`. For an explicit ODE, pass an `InitialValueProblem` to the public method directly or to `solve_ivp` with its method name. Neither interface requires an ARGESIM model or a DEVS scheduler. [ODE examples and aliases](../QSS_SOLVERS.md) · [DAE implementation](../argesim_benchmarks/solvers/dae.py) · [SUNDIALS mathematics](https://sundials.readthedocs.io/en/latest/ida/Mathematics_link.html) · [CasADi integrator interface](https://web.casadi.org/docs/)
