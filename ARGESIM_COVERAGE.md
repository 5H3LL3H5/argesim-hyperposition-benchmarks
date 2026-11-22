# Official ARGESIM coverage

The catalog and runner generate the status and CLI-task tables below. A family
can reach `validated` for a specific observable. The reference report gives
the applicable parameter set, comparison and tolerance. C18 has executable
algorithms and a reproducible figure demo, while the official data pair
remains outstanding. [Evidence gates](METHODOLOGY.md#evidence-gates) ·
[Reference comparisons](docs/PUBLISHED_REFERENCE_CHECKS.md) ·
[Official catalog](https://www.argesim.org/benchmarks)

<!-- BEGIN GENERATED BENCHMARK STATUS -->
| ID | Official benchmark | Model family | Status |
|---|---|---|---|
| C01 | Lithium-Cluster Dynamics | stiff ODE | validated |
| C02 | Flexible Assembly System | DES | implemented |
| C03 | Class-E Amplifier | ODE, hybrid | validated |
| C04 | Dining Philosophers | DES/concurrency | implemented |
| C05 | Two State Model | stiff ODE, state events | validated |
| C06 | Emergency Department - Follow-up Treatment | stochastic DES | validated |
| C07 | Constrained Pendulum | hybrid mechanics | validated |
| C08 | Canal-and-Lock System | stochastic DES | validated |
| C09 | Fuzzy Control of a Two Tank System | nonlinear ODE, sampled fuzzy control | implemented |
| C10 | Dining Philosophers II | DES/concurrency | implemented |
| C11 | SCARA Robot | DAE, hybrid control | implemented |
| C12 | Collision Processes in Rows of Spheres | hybrid mechanics, stochastic study | validated |
| C13 | Crane and Embedded Control | DAE, sampled control | validated |
| C14 | Supply Chain | discrete-time dynamics | implemented |
| C15 | Clearance Identification | ODE identification | validated |
| C16 | Restaurant Business Dynamics | agent-based stochastic dynamics | validated |
| C17R | SIR-type Epidemic with Cellular Automata and ODEs | ODE, FHP-I CA, interventions | validated |
| C18 | Identification of Nonlinear Dynamics - Neural Networks versus Transfer Functions | ARX, static/dynamic ANN | specified |
| C19R | Pollution in Groundwater Flow | PDE/distributed system | implemented |
| C20 | Complex Production System | stochastic production DES | implemented |
| C21 | State Events and Structural-dynamic Systems | ODE/DAE, hybrid | validated |
| C22 | Non-standard Queuing Policies | DES/queueing | validated |
| CP1 | Parallel Simulation Techniques | ODE, MOL/PDE, parallel study | validated |
| CP2 | Parallel and Distributed Simulation | Monte Carlo, LBM, implicit PDE/Fourier | validated |
<!-- END GENERATED BENCHMARK STATUS -->

## Available executable scope

Run a task with `python -m argesim_benchmarks run ID TASK`. Task names below
come from the runner registry. Each evidence note identifies the measured case.

<!-- BEGIN GENERATED EXECUTABLE SCOPE -->
| ID | Registered CLI tasks | Scope and evidence |
|---|---|---|
| C01 | `A`, `B`, `C` | Five Task B trajectories against Radau and two stationary states against Dymola. [Results](docs/C01_RESULTS.md) |
| C02 | `main`, `study` | Finite assembly plant and pallet study. Eleven CSIM loads pass under one convention. Default SimEvents gaps at 13, 14 and 25 pallets. [Clocks and comparison](docs/C02_IMPLEMENTATION.md) |
| C03 | `A`, `B`, `C` | Switch-state eigenvalues, half cycles and finite-ramp endpoints. [Results](docs/C03_VALIDATION_REPORT.md) |
| C04 | `run`, `compare`, `refinements` | Fork conservation, cleaning, deterministic replay and deadlock checks. Published fairness distributions remain open. |
| C05 | `simulate`, `validate`, `C`, `D` | Five default and 62 Task D switches, logarithmic crossing references and precision studies. |
| C06 | `A`, `B`, `C` | Three service policies and 21 daily metrics compared with 100-replication STROBOSCOPE results. |
| C07 | `A`, `B`, `C` | Nonlinear pin contact times and independent DOP853 trajectories for two initial conditions. |
| C08 | `replication`, `C` | Five published deterministic datasets for lock policies, plus stochastic replication tests. [Results](docs/C08_VALIDATION.md) |
| C09 | `run`, `validate` | Three fuzzy controllers. One of three Simulink figure measurements matches the definition-scale run. [Windows and control signal](docs/C09_FIGURE_CHECKS.md) |
| C10 | `A`, `B` | Simultaneous-access priority, deadlock termination and 50-run study. Matched waiting-time distributions remain open. |
| C11 | `A`, `B`, `C`, `main` | PD-controlled SCARA motion with bounded armature currents at accepted samples. A matched independent trajectory remains open. |
| C12 | `A`, `B`, `C` | Inverse restitution and the Dymola distribution of terminal speeds. |
| C13 | `A`, `B`, `C` | Linear Task A endpoints validated at three loads. B/C holding and emergency brake logic tested. [C13R evidence](docs/C13_REFERENCE_ANALYSIS.md) |
| C14 | `A1`, `A2`, `B1`, `B2`, `C1`, `C2` | D1 stock histories and 30-day cost and delivery studies. [Reference variants](docs/C14_VALIDATION.md) |
| C15 | `A`, `B`, `C` | Equal bolus dose at three infusion durations, Task B fit and a 1,000-sample parameter experiment. |
| C16 | `A`, `B`, `C` | Year-five restaurant count compared with two published studies. [Validation scope](docs/C16_VALIDATION.md) |
| C17R | `task1`, `compare`, `ca`, `ode` | Default ODE trajectories validated. The spatial FHP-I comparison uses a published single-run statistic. [C17R results](docs/PUBLISHED_REFERENCE_CHECKS.md#c17r-default-ode-and-spatial-comparison) |
| C18 | `all` | ARX, static and recurrent networks implemented. Figure reconstruction executable. Original training and validation recordings missing. [Provenance](docs/C18_FIGURE_RECONSTRUCTION.md) |
| C19R | `A`, `B`, `C` | Groundwater profiles, continuous and scheduled treatment. The 1 m grid retains spatial error at breakthrough and near the disks. [Accuracy](docs/PUBLISHED_REFERENCE_CHECKS.md#c19r-spatial-and-time-accuracy) |
| C20 | `replication`, `experiment` | Layout, blocking, rework and disruptions. 360 runs on three generated order books, 36 transport replays. [Experiment](docs/C20_EXPERIMENT_20261120.json) |
| C21 | `event-contact`, `dynamic-contact`, `pendulum-basic`, `pendulum-kick`, `rlc-diode` | Published contact and pendulum quantities, plus residual checks on three RLC realizations. |
| C22 | `basic`, `jockeying`, `reneging`, `classing` | Published jockeying, abandonment and class waiting-time records. |
| CP1 | `A`, `B`, `B-validate`, `C` | Serial/parallel RK4, pair and rope decompositions. Published ten-population endpoint for Task B. |
| CP2 | `1`, `2`, `3` | Monte Carlo, full-way D2Q9 parity and the corrected 499-unknown rope/Fourier comparison. |
<!-- END GENERATED EXECUTABLE SCOPE -->

## Solver applicability

| Backend | Valid scope in this repository | Current state |
|---|---|---|
| Euler | explicit ODE and MOL systems; reference baseline | implemented and tested |
| RK4 | explicit ODE and MOL systems | implemented and tested |
| RK23 | explicit Bogacki–Shampine 3(2) for nonstiff ODEs and hybrid segments | [order tests and measured comparison](docs/QSS_DEVS_HISTORY.md#two-embedded-rk-pairs-for-comparison) |
| ESDIRK32 | implicit Kværnø 3/2a for stiff ODEs and hybrid segments | [stability, three C05 switches and terminal states](docs/QSS_DEVS_HISTORY.md#evidence-at-the-same-physical-target) |
| RK45 | non-stiff explicit ODE and hybrid segments | implemented and tested |
| QSS1/QSS2 | autonomous explicit ODE/MOL and hybrid continuous modes | separate implementations, tested |
| Hybrid runtime | guards at accepted steps, cubic-Hermite localization, affine BQSS1 flights or endpoint switching, dimension-changing resets | classical and QSS backends |
| DES/NSA-DEVS | exact integer/rational macro time, microsteps, priority and FIFO ties | reusable scheduler plus adapters |
| Parallel runtime | ordered reusable thread/process workers and timing parity | CP1/CP2 |
| QSS3/QSS4 | higher-order smooth autonomous ODE/MOL sections | implemented and tested |
| BQSS1 | autonomous ODE with a backward quantized target and hysteresis | published stiff example, independent analytical and hybrid tests |
| Logarithmic QSS1/QSS2 | relative width with an absolute floor at each state update | [accuracy and cost across a decaying transient](docs/SOLVER_SELECTION.md) |
| CQSS1 | centered first-order quantization for suitable Hamiltonian systems | implemented and tested |
| LIQSS1/2/3 | linearly implicit quantized integration for stiff autonomous ODEs | implemented and tested |
| mLIQSS1/2 | coupled stiff state pairs | implemented and tested |
| mLIQSS3 | higher-order coupled stiff state-pair reference extension | implemented, experimental |
| eLIQSS1/2/3 | generalized linearly implicit quantized integration | implemented and tested |
| CheQSS1/2/3 | Chebyshev generalized linearly implicit quantized integration | implemented and tested |
| LIQSS2-BDF | mixed state/time integration with LIQSS2 and BDF1/2 | implemented and tested |
| IDAS (optional) | regular index-one residual systems with consistent initialization | [C21 diode trajectories and both model-specific reductions](docs/SOLVER_COMPARISON.md#a-direct-dae-check-on-the-c21-diode) |
| Higher-index DAE | requires a suitable reduced formulation | automatic index reduction is outside the runtime |

## Evidence boundaries

- The original C18 100 Hz measurements were not recovered by this audit.
  Figure reconstruction requires explicit selection; regular runs require both
  input datasets. CSV import checks sampling and retains hashes/provenance.
  Each published vector trace now has 2,000 reconstructed samples from 0.00 to 19.99 s.
- C09 records a passing pre-disturbance plateau and two open Simulink figure
  discrepancies. C13's independent linear reference covers Task A. C17R's
  deterministic reference covers the default ODE. Its spatial experiment
  compares a distribution of seeded runs with one published scalar.
- C19R requires spatial grid studies as well as a time integrator.
  The residual solver covers regular index-one DAEs. QSS operates on explicit
  continuous equations. Higher-index DAEs require a suitable formulation.
- C21 is `validated` against published event, pendulum and dynamic-contact
  values. CP2 is `validated` against the corrected peer-reviewed rope study,
  its analytical Fourier solution and the archived official LBM algorithm.
- CP1 is `validated` because its RK4 endpoint is checked against the official
  ten-population table. Timing numbers are always environment-specific and do
  not promote a model to `benchmark-ready`.
- `HyperTime` is restricted superdense time, not a complete hyperreal field.
