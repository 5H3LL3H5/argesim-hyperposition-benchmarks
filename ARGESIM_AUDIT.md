# ARGESIM implementation audit

## Checkpointed definition groups (2026-09-28)

`run-definitions` partitions all 71 registered tasks into six groups and
executes each task with exact definition-profile arguments in an isolated
process. A source-pinned, SHA-256 group manifest checkpoints every task and
supports verified resumption after failure or interruption. Filtered runs are
explicitly partial; timeout artifacts report a blocker and unknown memory as
null. The manifest distinguishes completion of registered tasks from complete
source-definition coverage; CP2:3 still lacks the full corrected rope study
in its registered comparison entry. No full group is claimed from these
runner contract tests, and no catalog evidence gate changed.

## Isolated diagnostic performance mode (2026-09-28)

`run-performance` runs selected tasks in fresh processes with an untimed
reference, configurable warm-up and at least nine odd repetitions. It requires
exact result parity before publishing median/IQR, records all raw times,
collects an untimed Python allocation probe and process peak RSS with platform
units, and writes task JSON plus an atomic SHA-256 manifest. It does not
check independent published references; these timings are diagnostic and do
not advance a benchmark to `benchmark-ready`. Volatile or stochastic outputs
that cannot satisfy exact parity become explicit failed evidence records.

## Suite evidence envelope (2026-09-28)

The suite runner now attaches a schema-versioned execution record to every
attempt, including failures. It captures effective default inputs, environment,
commit identity when available, UTC start and duration. Fields without a
uniform measurement or independent reference are null with explicit reasons.
This is execution provenance, not external validation or performance evidence.
No catalog gate was changed. Repeatable timing, per-task memory and solver work
measurements remain separate pending work.

Baseline audit date: 2026-08-17. Focused C19R–C22 delta review: 2026-09-28.
Definitions were checked against the official catalog and primary papers.
Gate meanings are defined in `METHODOLOGY.md`.

## Focused C19R–C22 review (2026-09-28)

This review used qualified `main` after PR #43 as its starting point and
reviewed each subsequent change against the latest merged `main`. It did not
repeat the previously qualified infrastructure review.

| Case | Primary material compared | Concrete result and remaining evidence |
|---|---|---|
| C19R | Revised definition, Tasks A–C | Task B ended at day 100 while Task C requests the continuous reference through day 150; the horizon was aligned. The source-cell approximation and finite-domain boundary choices still require numerical comparison at the prescribed sections; the horizon change alone is not validation. |
| C20 | Definition, workstation/product tables 1–2, operational scenario table 3 and failure table 5 | The checked workstation generations, process plans, order distributions and failure parameters agree with the implementation. Full-scale output has no archived independent quantitative comparison; the conveyor remains the documented reference-control abstraction. No code change was justified by this limited check. |
| C21 | Definition and published Modelica solution | Existing tests cover published pendulum stop time 7.5962714 s and three kick cases, plus event/dynamic contact checks. This is limited validation of these variants and tolerances, not a claim of complete solver or DAE validation. No new mismatch was established in the checked material. |
| C22 | Definition, sections 1, 2–4 and task list | Corrected ascending deterministic entity classes independently of descending operator calls, and exposed the deterministic lqt(t) step trace required for plotting. The tests verify the class prefix, first call, trace endpoints and integral; published queue traces and stochastic statistics have not been independently matched. |

## Focused suggestion review (2026-09-28)

The eight repository suggestions were checked against qualified `main` without
reopening the benchmark definitions. Two missing contract tests were confirmed:
`convergence_table` rejects an empty iterable, and generated status markers
must be present in the right order. Review of the latter also found a concrete
integrity gap: duplicate marker pairs could leave an extra, stale table in the
coverage document while the first generated table verified successfully.
The section replacement now requires exactly one start and end marker; direct
tests cover absent, reversed and duplicate markers.

The `math.log(0)` alert in the LIQSS root helper is unreachable: zero
polynomials are rejected, leading zero coefficients are removed, and a
constant-only polynomial exits before the logarithm. The two factorial
suggestions concern small fixed solver orders; C19R's distance calculations
occur once while selecting facility cells; and C16's distance replacement has
no representative end-to-end speedup or seeded-result parity evidence.
These performance changes were therefore not applied. The root-level
`parse_comments.py` placeholder has no registered benchmark task or specified
AST-comment contract; no parser was invented for it.

The unified runner registers all 24 active families, and its focused tests
check registry completeness, entrypoint resolution and single-task CLI use.
This does not claim that every default task can be executed as a bounded
one-command full-suite experiment. No scientific evidence gate changed.

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
| C07 | implemented | Explicit hybrid modes share classical/QSS event handling; Task C localizes the turning angle between solver samples and agrees with the published initial velocity to 1e-6. |
| C08 | validated | Independent table/replication checks pass. |
| C09 | implemented | I-FC1, I-FC2 and P-FC surfaces plus the complete 60,000 s experiment execute. The published Simulink `change-level` convention gives final I-FC errors below 0.02 mm and disturbance rejection; the contradictory literal printed error difference remains selectable. |
| C10 | implemented | Concurrency/deadlock tasks execute independently of C04, including the specified simultaneous-access priority and the Task-B minimum of 50 deadlock runs. |
| C11 | implemented | Official inertia coupling and nine-state explicit formulation execute; Tasks A/B/C are separate entry points and Task C returns x_tip, q3-h_obs and x_obs diagnostic trajectories. No implicit-formulation performance comparison is claimed. |
| C12 | implemented | Deterministic, boundary-value and stochastic collision tasks execute; the published quasi-plastic e=0.18 boundary and C1 restitution root are regression-checked. |
| C13 | implemented | Revised nonlinear/linear crane and embedded-control tasks execute with d_l=0.001 kg/s, 0.1 s digital-controller sampling, the specified Task-B/Task-C disturbance sequences, and complete load/brake/emergency diagnostic trajectories. The 2006 definition used d_l=0.01 kg/s and its published ~±294 m Task-A table belongs to that revision. An independent DOP853 integration of both parameter sets reproduces the ~±294 versus ~±299 m shift; smaller residual differences to the old table remain. [Analysis](docs/C13_REFERENCE_ANALYSIS.md). No 2007 external validation is claimed. |
| C14 | implemented | All discrete supply-chain tasks execute; the day-8 ten-piece initial fill is strategy-independent as specified, with strategy-specific ordering starting only afterwards. |
| C15 | implemented | Identification/Monte Carlo tasks and explicit bolus segments execute. |
| C16 | implemented | Agent/DES restaurant tasks preserve deterministic microstep ordering. |
| C17R | implemented | Task-1 sweeps, ODE/CA comparison, FHP-I collisions, homogeneous random movement, persistent soft measures and repeatable hard/spatial threshold interventions execute through classical or QSS2 hybrid paths; revised lattice sizing uses ceiling and discrete hard-measure populations are rounded down. The default high-contact sweep now uses C=5 and alpha=0.08: the earlier C=8 implied more people than six FHP slots per cell. |
| C18 | implemented | ARX, parallel residual ANN and free-running dynamic ANN execute and return models, trajectories, correlations and error trends on user data or provenance-labelled digitizations. Original measurement files remain an external-data gap, not a hidden substitution. |
| C19R | implemented | Three MOL tasks and analytical checks execute. The Task-B continuous run now extends to day 150 so its output can be compared with Task C on the interval specified by the definition. Independent reference trajectories and the required plots remain open evidence. |
| C20 | implemented | All 3x4 scenarios and 5000-order defaults execute with alternative process plans, workstation generations, constraints, repairs and median/IQR output. Source/inter-operation/sink transport uses a dimensioned two-ring network, 1 m/s belt speed, finite 1 m-part capacity and PSc4 failures/rerouting. |
| C21 | validated | Ball event/dynamic/shortcut studies, pendulum basic/kick studies and algebraic/interpolated/index-reduced Shockley RLC forms execute. Published stop time, kick angles, contact limits and dynamic-contact samples pass declared tolerances. |
| C22 | implemented | Four queue policies execute. Deterministic class assignment ascends from 1 while operator calls descend from 5 after t=10. Deterministic runs now expose the complete queue-length step trace needed for the prescribed lqt(t) plots; published trace/plot comparisons remain open before validation. |
| CP1 | validated | All three serial/parallel workloads execute; task-B endpoint matches the published table. |
| CP2 | validated | Sample/time Monte Carlo, reference full-way D2Q9 LBGK with reusable collision workers, and the corrected 499-unknown implicit/Fourier rope study execute. Serial/parallel LBM populations agree exactly; full rope traces/profiles stay below 5e-4/3e-4 error. |

## Primary completion sources

- [C05 semi-analytical solution](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C05/C5-solution-Maple-semi-analyt.pdf)
- [C13R revised definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C13/C13-definition-2.pdf) and [2006 comparison solution, page 30](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_16_1/sne.16.1.pdf)
- [C14 definition, Tables 1 and 3](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C14/C14-definition.pdf): on day eight, D1 and D2 each order ten p1 from F1 while D3 and D4 each order ten p1 from F4.
- [C04 comparative solution](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_28_1/articles/sne.28.1.10406.bn04.OA.pdf)
- [C09R definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C09/C9R-revised-definition.pdf) and [classic solution](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C09/C9R-solution-MATLAB-Simulink-Fuzzy.pdf)
- [C17R definition](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_25_1/articles/sne.25.1.10283.bn17r.OA.pdf)
- [C18 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-definition.pdf) and [classic MATLAB solution](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-solution-MATLAB-02.pdf)
- [C19R revised definition, Tasks B/C](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C19/C19-revised-definition.pdf): continuous and scheduled traces at (50,0) are compared from day 0 to 150.
- [C20 definition](https://www.argesim.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_21_34/articles/sne.21.34.10097.bn20.OA.pdf)
- [C21 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_26_2/articles/sne.26.2.10339.bn21.OA.pdf), [Modelica solution](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_28_2/articles/sne.28.2.10411.bn21.OA.pdf) and [Simulink solution](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_31_1/articles/sne.31.1.10556.bn21.OA.pdf)
- [C22 definition, section 4](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_29_3/articles/sne.29.3.10481.bn22.OA.pdf): deterministic entity classes ascend from 1; operator calls descend from 5.
- [CP1 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/CP/CP1-definition.pdf)
- [CP2 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/CP/CP2-definition.pdf), [corrected PDE/Monte-Carlo solution](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_32_4/articles/sne.32.4.10625.bncp2.OA.pdf), [LBM solution](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_33_2/articles/sne.33.2.10646.bncp2.OA.pdf) and [reference code](https://github.com/cea-wismar/ArgesimCP2)

## Deliberate non-claims

- Internal conservation or cross-form agreement is verification, not an
  independent published validation.
- The suite smoke profile establishes that entry points execute with shortened
  workloads. The definition profile keeps task defaults and required inputs;
  neither profile promotes a catalog evidence level.
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
