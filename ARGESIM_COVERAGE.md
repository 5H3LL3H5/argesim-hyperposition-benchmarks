# Official ARGESIM coverage

Inventory date: 2026-08-15. Primary catalog:
[ARGESIM Benchmarks](https://www.argesim.org/benchmarks).

`cataloged` means that the official identity and model family were checked. It
does **not** mean that equations, parameters, experiments and reference values
have already been implemented.

| ID | Official benchmark | Model family | Status |
|---|---|---|---|
| C01 | Lithium-Cluster Dynamics | stiff ODE | implemented |
| C02 | Flexible Assembly System | DES | validated |
| C03 | Class-E Amplifier | ODE, hybrid | implemented |
| C04 | Dining Philosophers | DES/concurrency | cataloged |
| C05 | Two State Model | stiff ODE, state events | cataloged |
| C06 | Emergency Department - Follow-up Treatment | stochastic DES | implemented |
| C07 | Constrained Pendulum | hybrid mechanics | implemented |
| C08 | Canal-and-Lock System | stochastic DES | validated |
| C09 | Fuzzy Control of a Two Tank System | hybrid sampled control | cataloged |
| C10 | Dining Philosophers II | DES/concurrency | implemented |
| C11 | SCARA Robot | DAE, hybrid control | implemented |
| C12 | Collision Processes in Rows of Spheres | hybrid mechanics, stochastic study | implemented |
| C13 | Crane and Embedded Control | DAE, sampled control | implemented |
| C14 | Supply Chain | discrete-time dynamics | implemented |
| C15 | Clearance Identification | ODE identification | implemented |
| C16 | Restaurant Business Dynamics | agent-based stochastic dynamics | implemented |
| C17R | SIR-type Epidemic with Cellular Automata and ODEs | ODE, CA, identification | specified (ODE part) |
| C18 | Identification of Nonlinear Dynamics | transfer functions, neural networks | cataloged |
| C19R | Pollution in Groundwater Flow | PDE/distributed system | implemented |
| C20 | Complex Production System | DES | specified (partial runtime/model) |
| C21 | State Events and Structural-dynamic Systems | ODE/DAE, hybrid | specified (RLC incomplete) |
| C22 | Non-standard Queuing Policies | DES/queueing | implemented |
| CP1 | Parallel Simulation Techniques | ODE, MOL/PDE, parallel study | specified (models only) |
| CP2 | Parallel and Distributed Simulation | Monte Carlo, LBM, MOL/PDE | specified (kernels only) |

## Solver applicability

| Backend | Valid scope in this repository | Current state |
|---|---|---|
| Euler | explicit ODE and MOL systems; reference baseline | implemented and tested |
| RK4 | explicit ODE and MOL systems | implemented and tested |
| RK45 | non-stiff explicit ODE and MOL systems | implemented and tested |
| QSS1 | autonomous explicit ODE and MOL systems | implemented and tested |
| QSS2 | autonomous explicit ODE/MOL and hybrid continuous modes | implemented and tested |
| LIQSS | compatible stiff ODE/MOL structures | not implemented |
| Hybrid runtime | directed guards, localized transitions, mode/state reset | RK/Euler and QSS1/QSS2 backends |
| DES/NSA-DEVS | deterministic callback DES and restricted superdense time | reusable scheduler plus benchmark adapters |
| Neural operator | trained surrogate for a fixed PDE family | not integrated |

`implemented` for C01 means that all three official tasks are represented:
task A exposes Euler, RK4, RK45, QSS1 and QSS2 runs plus an accuracy-gated timing
driver; task B retains complete trajectories for the requested logarithmic
loss-rate sweep; task C uses and verifies the analytical steady states. It is
not yet `validated` because an independent published trajectory table or
cross-tool reference data set has not been archived.

Partial modules never inherit the status of their finished kernels: C17R lacks
the cellular-automaton, identification and intervention tasks; C21 lacks the
complete RLC/diode DAE variants; CP1/CP2 lack the required parallel experiments.

Euler, RK4 and RK45 are not applied to an unreduced DAE. QSS is applied to a
PDE only after spatial discretization. A neural operator will be evaluated as
a trained problem-family surrogate, never as a universal PDE solver.
