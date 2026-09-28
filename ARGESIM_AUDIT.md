# ARGESIM implementation audit

Audit date: 2026-08-17. Definitions were checked against the official catalog
and primary papers. Gate meanings are defined in `METHODOLOGY.md`.

## Runtime separation

| Concern | Reusable implementation | Benchmark use |
|---|---|---|
| Explicit ODE | separate Euler, RK4 and adaptive RK45 | continuous benchmark families |
| Quantized ODE | QSS1-4, CQSS1, LIQSS1-3, mLIQSS1-3 and LIQSS2-BDF | C01, C07, C11, C15, C17R, C21 |
| Hybrid events | directed guards, cubic-Hermite localization, optional fixed-step endpoint semantics, state/mode reset | C05, C07, C17R, C21 |
| Callback DES | deterministic `HyperTime` scheduler and event caps | DES families and C20 components |
| Parallel execution | persistent ordered executor, warm-up, repeat samples and parity error | CP1 and CP2 |
| PDE | explicit MOL, implicit tridiagonal time stepping and analytical references | C19R, CP1, CP2 |

The event layer is independent of its continuous solver. Benchmark policy stays
inside the model; event ordering, executor lifetime and timing summaries stay
in shared runtime code.

## Per-definition result

| ID | Gate | Audit result |
|---|---|---|
| C01 | implemented | Tasks A-C and five solver selections execute; independent published trajectories are not archived. |
| C02 | validated | Published throughput/transit references pass. |
| C03 | implemented | Switch boundaries are aligned; non-autonomous QSS misuse is rejected. |
| C04 | implemented | Unsafe, waiter, cleaning/ordered-fork and put-back strategies execute with seeded replications, resource-cycle deadlock detection, per-philosopher meals/fairness and complete state-time accounting. C10 remains a separate definition. |
| C05 | validated | Closed-form modes reproduce five default events, all 62 Task-D events and both published endpoints. |
| C06 | implemented | Shared DES scheduling executes all three tasks; Task B preserves two-doctor ward capacity and models the specified hysteretic CW1/CW2 doctor-time exchange by alternating the two service distributions in each aggregate two-server ward. Persistent individual server identity is not claimed. |
| C07 | implemented | Explicit hybrid modes share classical/QSS event handling; Task C reproduces the published initial angular velocity for the -pi/2 target within declared tolerance. |
| C08 | validated | Independent table/replication checks pass. |
| C09 | implemented | I-FC1, I-FC2 and P-FC surfaces plus the complete 60,000 s experiment execute. The published Simulink `change-level` convention gives final I-FC errors below 0.02 mm and disturbance rejection; the contradictory literal printed error difference remains selectable. |
| C10 | implemented | Concurrency/deadlock tasks execute independently of C04, including the specified simultaneous-access priority and the Task-B minimum of 50 deadlock runs. |
| C11 | implemented | Official inertia coupling and nine-state explicit formulation execute; Tasks A/B/C are separate entry points and Task C returns x_tip, q3-h_obs and x_obs diagnostic trajectories. No implicit-formulation performance comparison is claimed. |
| C12 | implemented | Deterministic, boundary-value and stochastic collision tasks execute; the published quasi-plastic e=0.18 boundary and C1 restitution root are regression-checked. |
| C13 | implemented | Revised nonlinear/linear crane and embedded-control tasks execute with d_l=0.001 kg/s, 0.1 s digital-controller sampling, the specified Task-B/Task-C disturbance sequences, and complete load/brake/emergency diagnostic trajectories. |
| C14 | implemented | All discrete supply-chain tasks execute; the day-8 ten-piece initial fill is strategy-independent as specified, with strategy-specific ordering starting only afterwards. |
| C15 | implemented | Identification/Monte Carlo tasks and explicit bolus segments execute. |
| C16 | implemented | Agent/DES restaurant tasks preserve deterministic microstep ordering. |
| C17R | implemented | Task-1 sweeps, ODE/CA comparison, FHP-I collisions, homogeneous random movement, persistent soft measures and repeatable hard/spatial threshold interventions execute through classical or QSS2 hybrid paths; revised lattice sizing uses ceiling and discrete hard-measure populations are rounded down. |
| C18 | implemented | ARX, parallel residual ANN and free-running dynamic ANN execute and return models, trajectories, correlations and error trends on user data or provenance-labelled digitizations. Original measurement files remain an external-data gap, not a hidden substitution. |
| C19R | implemented | Three MOL tasks and analytical checks execute. |
| C20 | implemented | All 3x4 scenarios and 5000-order defaults execute with alternative process plans, workstation generations, constraints, repairs and median/IQR output. Source/inter-operation/sink transport uses a dimensioned two-ring network, 1 m/s belt speed, finite 1 m-part capacity and PSc4 failures/rerouting. |
| C21 | validated | Ball event/dynamic/shortcut studies, pendulum basic/kick studies and algebraic/interpolated/index-reduced Shockley RLC forms execute. Published stop time, kick angles, contact limits and dynamic-contact samples pass declared tolerances. |
| C22 | implemented | Four queue policies execute. The deterministic class assignment follows the definition's ascending 1..5 cycle; the operator's independent call order descends from 5 after t=10. Concurrency and published trace/plot evidence remain to be reviewed before validation. |
| CP1 | validated | All three serial/parallel workloads execute; task-B endpoint matches the published table. |
| CP2 | validated | Sample/time Monte Carlo, reference full-way D2Q9 LBGK with reusable collision workers, and the corrected 499-unknown implicit/Fourier rope study execute. Serial/parallel LBM populations agree exactly; full rope traces/profiles stay below 5e-4/3e-4 error. |

## Primary completion sources

- [C05 semi-analytical solution](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C05/C5-solution-Maple-semi-analyt.pdf)
- [C04 comparative solution](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_28_1/articles/sne.28.1.10406.bn04.OA.pdf)
- [C09R definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C09/C9R-revised-definition.pdf) and [classic solution](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C09/C9R-solution-MATLAB-Simulink-Fuzzy.pdf)
- [C17R definition](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_25_1/articles/sne.25.1.10283.bn17r.OA.pdf)
- [C18 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-definition.pdf) and [classic MATLAB solution](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-solution-MATLAB-02.pdf)
- [C20 definition](https://www.argesim.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_21_34/articles/sne.21.34.10097.bn20.OA.pdf)
- [C21 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_26_2/articles/sne.26.2.10339.bn21.OA.pdf), [Modelica solution](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_28_2/articles/sne.28.2.10411.bn21.OA.pdf) and [Simulink solution](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_31_1/articles/sne.31.1.10556.bn21.OA.pdf)
- [C22 definition, section 4](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_29_3/articles/sne.29.3.10481.bn22.OA.pdf): deterministic entity classes ascend from 1; operator calls descend from 5.
- [CP1 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/CP/CP1-definition.pdf)
- [CP2 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/CP/CP2-definition.pdf), [corrected PDE/Monte-Carlo solution](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_32_4/articles/sne.32.4.10625.bncp2.OA.pdf), [LBM solution](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_33_2/articles/sne.33.2.10646.bncp2.OA.pdf) and [reference code](https://github.com/cea-wismar/ArgesimCP2)

## Deliberate non-claims

- Internal conservation or cross-form agreement is verification, not an
  independent published validation.
- A hardware-dependent speedup is reported, never required to exceed one.
- The 2007 CP2 text printed `nu=0.6`; the peer-reviewed 2022 correction and
  reference code specify `nu=0.06`, 0-10 s, and profiles at 5 s and 8 s. The
  printed variant remains available explicitly for provenance experiments.
- C20's conveyor is a dimensioned reference-control abstraction of the
  published two-ring layout, not a claim to encode every drawing junction and
  buffer as an individual object.
- C18 reports teacher-forced and free-running dynamic-ANN metrics separately;
  the former is not presented as closed-loop simulation evidence.
- No general-purpose implicit DAE solver is claimed. Quantized partitions are
  limited to autonomous ODEs; the full BDF partition may be non-autonomous.
