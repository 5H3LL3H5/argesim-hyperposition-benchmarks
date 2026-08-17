# Official ARGESIM coverage

Inventory date: 2026-08-17. Primary catalog:
[ARGESIM Benchmarks](https://www.argesim.org/benchmarks).

The status is an evidence gate, not a code-size label. `implemented` means all
required task types have an executable path and tests; `validated` additionally
requires an external analytical or published numeric reference.

| ID | Official benchmark | Model family | Status |
|---|---|---|---|
| C01 | Lithium-Cluster Dynamics | stiff ODE | implemented |
| C02 | Flexible Assembly System | DES | validated |
| C03 | Class-E Amplifier | ODE, hybrid | implemented |
| C04 | Dining Philosophers | DES/concurrency | implemented |
| C05 | Two State Model | stiff ODE, state events | validated |
| C06 | Emergency Department - Follow-up Treatment | stochastic DES | implemented |
| C07 | Constrained Pendulum | hybrid mechanics | implemented |
| C08 | Canal-and-Lock System | stochastic DES | validated |
| C09 | Fuzzy Control of a Two Tank System | nonlinear ODE, sampled fuzzy control | implemented |
| C10 | Dining Philosophers II | DES/concurrency | implemented |
| C11 | SCARA Robot | DAE, hybrid control | implemented |
| C12 | Collision Processes in Rows of Spheres | hybrid mechanics, stochastic study | implemented |
| C13 | Crane and Embedded Control | DAE, sampled control | implemented |
| C14 | Supply Chain | discrete-time dynamics | implemented |
| C15 | Clearance Identification | ODE identification | implemented |
| C16 | Restaurant Business Dynamics | agent-based stochastic dynamics | implemented |
| C17R | SIR Epidemic with CA and ODEs | ODE, FHP-I CA, interventions | implemented |
| C18 | Identification of Nonlinear Dynamics | ARX, static/dynamic ANN | implemented |
| C19R | Pollution in Groundwater Flow | PDE/distributed system | implemented |
| C20 | Complex Production System | stochastic production DES | implemented |
| C21 | State Events and Structural-dynamic Systems | ODE/DAE, hybrid | validated |
| C22 | Non-standard Queuing Policies | DES/queueing | implemented |
| CP1 | Parallel Simulation Techniques | ODE, MOL/PDE, parallel study | validated |
| CP2 | Parallel and Distributed Simulation | Monte Carlo, LBM, implicit PDE/Fourier | validated |

## Newly completed benchmark scope

| ID | Executable scope | Verification evidence |
|---|---|---|
| C04 | Unsafe, waiter, clean/ordered-fork and put-back strategies; seeded replications, per-philosopher fairness and full state-time accounting | conservation of every individual horizon, deterministic replay, resource-cycle deadlock/progress tests |
| C05 | exact piecewise solution, state switching, default experiment and 62-event Task D | published event times to about 2e-12 s; published final values |
| C09 | I-FC1, I-FC2 and P-FC surfaces; nonlinear tanks; 1 s sampled 60,000 s scenario; reference `change-level` and literal printed difference modes | I-FC final errors below 0.02 mm, <0.06 mm setpoint overshoot and published qualitative disturbance/P-FC behaviour |
| C17R | identified ODE, hexagonal FHP-I CA, homogeneous random movement, Task-1 sweeps and persistent soft/repeatable hard/spatial interventions | population conservation, lattice/contact equation, seeded replay and shared RK/QSS2 hybrid-event paths |
| C18 | second-order ARX, seven-unit parallel residual ANN and ten-unit free-running dynamic ANN; complete trajectories and error trends | synthetic coefficient recovery; digitized-figure ARX correlations 0.962/0.942 versus published 0.95/0.94; provenance gap retained |
| C20 | three order scenarios, four plant scenarios, all plans/machines, due dates, setups, tool changes, repair-safe starts and dimensioned finite-capacity conveyor failures | all 12 scenario paths complete reduced order books; full 5000-order paths complete; deterministic seeded generation |
| C21 | event/dynamic ball studies, pendulum basic/kick studies, and algebraic/interpolated/index-reduced Shockley RLC variants | published pendulum stop/kick values, event contact limits and dynamic-contact samples plus algebraic residual below 1e-8 |
| CP1 | 1000-run RK4 study, five-pair ODE decomposition and 800-line rope MOL decomposition | serial/parallel bitwise parity; published task-B terminal table |
| CP2 | two Monte Carlo distribution strategies, official full-way D2Q9 LBGK with output field, reusable row workers, corrected 499-unknown rope traces/profiles/surface and Fourier reference | exact serial/parallel LBM parity and reference boundary; corrected full rope errors below 5e-4/3e-4 |

## Solver applicability

| Backend | Valid scope in this repository | Current state |
|---|---|---|
| Euler | explicit ODE and MOL systems; reference baseline | implemented and tested |
| RK4 | explicit ODE and MOL systems | implemented and tested |
| RK45 | non-stiff explicit ODE and hybrid segments | implemented and tested |
| QSS1/QSS2 | autonomous explicit ODE/MOL and hybrid continuous modes | separate implementations, tested |
| Hybrid runtime | directed guards, cubic-Hermite localized transitions, optional fixed-step endpoint semantics, dimension-changing reset | classical and QSS backends |
| DES/NSA-DEVS | deterministic callbacks and restricted superdense time | reusable scheduler plus adapters |
| Parallel runtime | ordered reusable thread/process workers and timing parity | CP1/CP2 |
| LIQSS | linearly implicit quantized integration | not implemented |
| General implicit DAE | arbitrary high-index DAE | not implemented; C21 uses its specified index-1 reduction |

## Evidence boundaries

- The original C18 100 Hz downloads are unavailable. The bundled data are
  explicitly labelled 5 Hz vector-figure digitizations interpolated to the
  specified grid; callers can supply recovered original files without changing
  the algorithms.
- C09, C17R and C20 have internal/cross-form or qualitative published checks
  but no archived independent numeric full-output reference, so they remain
  `implemented`.
- C21 is `validated` against published event, pendulum and dynamic-contact
  values. CP2 is `validated` against the corrected peer-reviewed rope study,
  its analytical Fourier solution and the archived official LBM algorithm.
- CP1 is `validated` because its RK4 endpoint is checked against the official
  ten-population table. Timing numbers are always environment-specific and do
  not promote a model to `benchmark-ready`.
- `HyperTime` is restricted superdense time, not a complete hyperreal field.
