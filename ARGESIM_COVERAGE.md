# Official ARGESIM coverage

Inventory reviewed on 2026-11-20. See the [published numerical comparisons](docs/PUBLISHED_REFERENCE_CHECKS.md) and the primary catalog,
[ARGESIM Benchmarks](https://www.argesim.org/benchmarks).

The status is an evidence gate, not a code-size label. `implemented` means all
required task types have an executable path and tests; `validated` additionally
requires an external analytical or published numeric reference. Partial code stays
`specified`; see the follow-up audit for C18 and its outstanding measurement data.

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
| C13 | Crane and Embedded Control | DAE, sampled control | implemented |
| C14 | Supply Chain | discrete-time dynamics | implemented |
| C15 | Clearance Identification | ODE identification | validated |
| C16 | Restaurant Business Dynamics | agent-based stochastic dynamics | validated |
| C17R | SIR-type Epidemic with Cellular Automata and ODEs | ODE, FHP-I CA, interventions | implemented |
| C18 | Identification of Nonlinear Dynamics - Neural Networks versus Transfer Functions | ARX, static/dynamic ANN | specified |
| C19R | Pollution in Groundwater Flow | PDE/distributed system | implemented |
| C20 | Complex Production System | stochastic production DES | implemented |
| C21 | State Events and Structural-dynamic Systems | ODE/DAE, hybrid | validated |
| C22 | Non-standard Queuing Policies | DES/queueing | validated |
| CP1 | Parallel Simulation Techniques | ODE, MOL/PDE, parallel study | validated |
| CP2 | Parallel and Distributed Simulation | Monte Carlo, LBM, implicit PDE/Fourier | validated |
<!-- END GENERATED BENCHMARK STATUS -->

## Available executable scope

| ID | Executable scope | Verification evidence |
|---|---|---|
| C02 | finite B1/B2 assembly plant, exclusive shifters, parameter study over 1–60 pallets | single-pallet cycle, FIFO/merge replay, deadlock wait sets and finite-window accounting. Three of 12 starting seeds match 11/12 SimEvents rows under service-only timing. [Reference comparisons](C02_IMPLEMENTATION.md) |
| C04 | Atomic, unsafe, waiter, cleaning, neighbour-request and put-back policies; dirty-fork delays, request age priority, explicit hoarding/targeted-hold experiments | conservation of every individual horizon, deterministic replay, resource-cycle deadlock/progress tests |
| C05 | sampled piecewise solution including fast transients, default/62-event Task D, decimal precision studies at the specified accuracies | published event checks; 80-digit reference, independently checked by 90-digit logarithmic event calculations; requested and attained precision reported separately |
| C09 | I-FC1, I-FC2 and P-FC surfaces; nonlinear tanks; 1 s sampled 60,000 s scenario; reference `change-level` and literal printed difference modes | I-FC final errors below 0.02 mm, <0.06 mm setpoint overshoot and published qualitative disturbance/P-FC behaviour |
| C17R | identified ODE, hexagonal FHP-I CA, homogeneous random movement, Task-1 sweeps and persistent soft/repeatable hard/spatial interventions | population conservation, lattice/contact equation, seeded replay and shared RK/QSS2 hybrid-event paths |
| C18 | second-order ARX, static residual ANN and repeated dynamic ANN fitting to the full output-feedback trajectory | published ARX gives 0.95347/0.94231 on the two digitized curves. [Reconstruction and independent validation results](docs/C18_FIGURE_RECONSTRUCTION.md) |
| C20 | 284-node/368-track causal layout, 90 buffer slots, 19 located machines, downstream blocking, source/sink/rework, setups, disruptions and Task A–D statistics | 360 runs of 5,000 orders across three generated books and 12 scenarios, with 36 full transport replays. External order-book parity is open. [Archived runs](docs/C20_EXPERIMENT_20261120.json) |
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
| QSS3/QSS4 | higher-order smooth autonomous ODE/MOL sections | implemented and tested |
| CQSS1 | centered first-order quantization for suitable Hamiltonian systems | implemented and tested |
| LIQSS1/2/3 | linearly implicit quantized integration for stiff autonomous ODEs | implemented and tested |
| mLIQSS1/2 | coupled stiff state pairs | implemented and tested |
| mLIQSS3 | higher-order coupled stiff state-pair reference extension | implemented, experimental |
| eLIQSS1/2/3 | generalized linearly implicit quantized integration | implemented and tested |
| CheQSS1/2/3 | Chebyshev generalized linearly implicit quantized integration | implemented and tested |
| LIQSS2-BDF | mixed state/time integration with LIQSS2 and BDF1/2 | implemented and tested |
| General implicit DAE | arbitrary high-index DAE | not implemented; C21 uses its specified index-1 reduction |

## Evidence boundaries

- The original C18 100 Hz measurements were not recovered by this audit.
  Figure reconstruction requires explicit selection; regular runs require both
  input datasets. CSV import checks sampling and retains hashes/provenance.
  Each published vector trace now has 2,000 reconstructed samples from 0.00 to 19.99 s.
- C09 and C17R have internal/cross-form or qualitative published checks
  but no archived independent numeric full-output reference, so they remain
  `implemented`.
- C21 is `validated` against published event, pendulum and dynamic-contact
  values. CP2 is `validated` against the corrected peer-reviewed rope study,
  its analytical Fourier solution and the archived official LBM algorithm.
- CP1 is `validated` because its RK4 endpoint is checked against the official
  ten-population table. Timing numbers are always environment-specific and do
  not promote a model to `benchmark-ready`.
- `HyperTime` is restricted superdense time, not a complete hyperreal field.
