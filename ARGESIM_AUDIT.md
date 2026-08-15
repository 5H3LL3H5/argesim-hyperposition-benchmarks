# ARGESIM implementation audit

Audit date: 2026-08-15. Definitions were checked from the
[official ARGESIM catalog](https://www.argesim.org/benchmarks/) and linked
primary definition papers. The evidence-gate meanings are defined in
`METHODOLOGY.md`.

## Runtime separation

| Concern | Reusable implementation | Benchmark use |
|---|---|---|
| Explicit ODE | independent Euler, RK4 and adaptive RK45 modules | C01, C03, C07, C11, C15, C17R, C19R, CP1/CP2 kernels |
| Quantized ODE | independent QSS1 and QSS2 modules | C01, C07, C11, C15, C17R, C21 |
| Solver selection | strict `solve_ivp` dispatcher; unknown options fail | shared model wrapper contract |
| Piecewise input | contiguous autonomous segments plus checked merge | C03 switch boundaries, C15 bolus switch |
| Hybrid state events | directed guards, localized roots, resets and mode changes | C07 and C21 classical/QSS execution |
| Callback DES | deterministic `HyperTime` scheduler with cancellation and event cap | C06 and partial C20 model |
| DEVS/NSA ordering | macro time plus ordered microsteps | C02, C08, C10, C22 and relay reference |

The hybrid layer is deliberately independent of the continuous solver. This
allows one state-event model to run in a classical continuous world or with a
DEVS-style QSS1/QSS2 backend. A benchmark-specific queue policy remains model
logic; event ordering and progress protection belong to the shared runtime.

## Per-definition findings

| ID | Gate | Review result and remaining boundary |
|---|---|---|
| C01 | implemented | Tasks A-C and all five solver choices are executable; no archived independent trajectory reference yet. |
| C02 | validated | Tasks track the published throughput/transit table within declared tolerances, including its deadlock region. |
| C03 | implemented | Switch boundaries are solver-aligned; QSS is correctly refused for the directly time-driven RHS. |
| C04 | cataloged | Official identity only; no C04 executable model. |
| C05 | cataloged | The stiff two-state/state-event definition has no executable model. |
| C06 | implemented | Uses shared DES scheduling. Task B now swaps doctors without changing 2/2 capacity and slows the transferred CW2 doctor in CW1 by 20%. |
| C07 | implemented | Long/short pendulum dynamics are explicit modes; the mode no longer changes inside root localization before the velocity reset. RK45 and QSS2 share the event model. |
| C08 | validated | Independent table/replication checks are present; the model already composes the shared DES scheduler. |
| C09 | cataloged | Continuous tanks plus sampled fuzzy controller are not implemented. |
| C10 | implemented | Concurrency and deadlock tasks are executable; this does not substitute for C04. |
| C11 | implemented | The official mixed inertia coefficient is `(m2/2 + m3) L1 L2`; QSS defaults now cover all nine states and QSS2 is selectable. |
| C12 | implemented | Deterministic, boundary-value and stochastic collision tasks are present; validation remains internal. |
| C13 | implemented | Nonlinear/linear crane and embedded-control tasks are present; a general implicit DAE solver is still outside the runtime. |
| C14 | implemented | All discrete supply-chain tasks are executable. |
| C15 | implemented | Identification and Monte Carlo tasks are present; QSS1/QSS2 use the explicit bolus switch as two autonomous segments. |
| C16 | implemented | Agent/DES restaurant tasks are executable with seeded stochastic runs. |
| C17R | specified | The ODE model is executable with classical and QSS solvers; cellular automaton, identification and intervention tasks are missing. |
| C18 | cataloged | Required identification datasets, transfer functions and neural-network comparisons are absent. |
| C19R | implemented | All three MOL tasks are present. Grid/parameter contracts and the analytical point-source singularity are explicit; no implicit stiff solver is claimed. |
| C20 | specified | Order books and workstation/conveyor components use isolated RNG and shared scheduling; the full production-control experiments are incomplete. |
| C21 | specified | Bouncing ball and rotating pendulum now share classical/QSS hybrid execution; the RLC-diode DAE task remains explicitly unimplemented. |
| C22 | implemented | First arrival is at `t=1`; concurrency priorities match the four policies; reneging cannot terminate an entity twice; classing observes the initial `tC=10` wait. |
| CP1 | specified | The three numerical model families and published task-B terminal values are present; required parallel execution/performance studies are not. |
| CP2 | specified | Monte Carlo IVP, D2Q9 step and rope MOL kernels are present; complete workloads and distributed comparisons are not. |

## Deliberate non-claims

- `HyperTime` is a restricted superdense-time representation, not the complete
  hyperreal field.
- QSS2 is an event-driven ODE backend; it is not LIQSS and not an implicit DAE
  solver.
- A partial benchmark kernel does not satisfy every official task and therefore
  cannot advance past `specified`.
- Only C02 and C08 currently have archived independent reference checks strong
  enough for the `validated` gate.
