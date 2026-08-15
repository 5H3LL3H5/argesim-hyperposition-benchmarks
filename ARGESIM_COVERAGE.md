# Official ARGESIM coverage

Inventory date: 2026-08-06. Primary catalog:
[ARGESIM Benchmarks](https://www.argesim.org/benchmarks).

`cataloged` means that the official identity and model family were checked. It
does **not** mean that equations, parameters, experiments and reference values
have already been implemented.

| ID | Official benchmark | Model family | Status |
|---|---|---|---|
| C01 | Lithium-Cluster Dynamics | stiff ODE | implemented |
| C02 | Flexible Assembly System | DES | implemented |
| C03 | Class-E Amplifier | ODE, hybrid | implemented |
| C04 | Dining Philosophers | DES/concurrency | cataloged |
| C05 | Two State Model | stiff ODE, state events | cataloged |
| C06 | Emergency Department - Follow-up Treatment | stochastic DES | implemented |
| C07 | Constrained Pendulum | hybrid mechanics | implemented |
| C08 | Canal-and-Lock System | stochastic DES | cataloged |
| C09 | Fuzzy Control of a Two Tank System | hybrid sampled control | cataloged |
| C10 | Dining Philosophers II | DES/concurrency | cataloged |
| C11 | SCARA Robot | DAE, hybrid control | implemented |
| C12 | Collision Processes in Rows of Spheres | hybrid mechanics, stochastic study | cataloged |
| C13 | Crane and Embedded Control | DAE, sampled control | implemented |
| C14 | Supply Chain | discrete-time dynamics | cataloged |
| C15 | Clearance Identification | ODE identification | cataloged |
| C16 | Restaurant Business Dynamics | agent-based stochastic dynamics | cataloged |
| C17R | SIR-type Epidemic with Cellular Automata and ODEs | ODE, CA, identification | implemented |
| C18 | Identification of Nonlinear Dynamics | transfer functions, neural networks | cataloged |
| C19R | Pollution in Groundwater Flow | PDE/distributed system | implemented |
| C20 | Complex Production System | DES | specified |
| C21 | State Events and Structural-dynamic Systems | ODE/DAE, hybrid | cataloged |
| C22 | Non-standard Queuing Policies | DES/queueing | implemented |
| CP1 | Parallel Simulation Techniques | ODE, MOL/PDE, parallel study | implemented |
| CP2 | Parallel and Distributed Simulation | Monte Carlo, LBM, MOL/PDE | implemented |

## Solver applicability

| Backend | Valid scope in this repository | Current state |
|---|---|---|
| Euler | explicit ODE and MOL systems; reference baseline | implemented and tested |
| RK4 | explicit ODE and MOL systems | implemented and tested |
| RK45 | non-stiff explicit ODE and MOL systems | implemented and tested |
| QSS1 | autonomous explicit ODE and MOL systems | implemented and tested |
| QSS2 | piecewise-linear quantized trajectories | implemented and tested |
| LIQSS | compatible stiff ODE/MOL structures | not implemented |
| DES/NSA-DEVS | discrete and hybrid event execution | restricted relay reference only |
| Neural operator | trained surrogate for a fixed PDE family | not integrated |

`implemented` for C01 means that all three official tasks are represented:
task A exposes Euler, RK4, RK45 and QSS1 runs plus an accuracy-gated timing
driver; task B retains complete trajectories for the requested logarithmic
loss-rate sweep; task C uses and verifies the analytical steady states. It is
not yet `validated` because an independent published trajectory table or
cross-tool reference data set has not been archived.

`implemented` for C02 includes formal internal/external DEVS scheduling,
finite B2 capacities, the published A2 and A3--A6 routing rules, warm-up and
measurement windows, and explicit detection of the published 50--60 pallet
deadlock region. Selected results reproduce the independent 2011 reference
table within six percent; the remaining difference is retained transparently
rather than being mislabeled as bit-for-bit validation.

Euler, RK4 and RK45 are not applied to an unreduced DAE. QSS is applied to a
PDE only after spatial discretization. A neural operator will be evaluated as
a trained problem-family surrogate, never as a universal PDE solver.
