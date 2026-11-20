# ARGESIM implementation audit

## Current reference results

The [reference comparison](docs/PUBLISHED_REFERENCE_CHECKS.md) records the current
scope for all 24 families, including the remaining C02 and C18 differences. The
full C20 experiment covers 360 runs on three generated books. Its independent
transport replays cover 55,648,862 events. [C20 evidence](docs/ARGESIM_CLOSURE_20261120.md)

## C02 initial positions and C18 feedback training, 2026-11-20

With the service-only positioning assumption, three of twelve fixed initial
seeds give 1,440 completions and 265 s at 14 pallets. Each of those three
seeds meets 11/12 SimEvents rows. The 25-pallet mean stays outside the 6%
band for all twelve seeds. [C02 experiments](C02_IMPLEMENTATION.md)

C18 Task C now fits the entire output-feedback trajectory for up to 50 epochs
per seed. The selected training run gives correlations of 0.99377 on the
training muscle and 0.92642 on the held-out muscle. The measurement files
remain unavailable. [C18 experiment](docs/C18_FIGURE_RECONSTRUCTION.md)

## C02 timing and C18 published curves, 2026-11-20

C02 now wakes A3 on physical arrival at the A6 input. The exclusive-unit
experiment reproduces all 60 archived numerical rows. Assigning approach and
clearance to the adjoining transport gives 10 of 12 SimEvents rows within
the same 6% band. The independent 25-pallet window balance closes exactly
under both assumptions. See the [C02 comparisons](C02_IMPLEMENTATION.md).

C18's digitization now recovers four 2,000-sample curves. The published
linear coefficients give 0.95347/0.94231 training/validation correlation.
Task C repeats training, ranks candidates on training rollouts and evaluates
the selected model on the second recording. The original measurement files
remain outstanding. See the [C18 evidence](docs/C18_FIGURE_RECONSTRUCTION.md).

## C02 finite transport and pallet study, 2026-11-20

The registered C02 solver runs the 1–60 pallet study with finite belts and
exclusive shifters. One pallet completes a full cycle in 191.67 s. The
default controller meets both SimEvents reference measures at 9 of 12
published numeric loads, including 10, 20 and 40 pallets. At 13 and 14
both measures are outside the 6% band, and at 25 the mean is outside it.
All 50–60 pallet runs admit the full population, then reach a closed wait
cycle. On the paper's own numbers, 14 cannot minimize its printed objective.
The CLI also evaluates that expression over its published range. C02 reaches
`implemented`. See the [C02 comparison and evidence](C02_IMPLEMENTATION.md).

## Routing, numerical and experiment follow-up, 2026-11-20

C02 now prevents assembly of empty pallets, interleaving A2 with an unfinished
A3/A4/A5 group, and overbooking branch slots through simultaneous DEVS arrivals.
C18 uses a scaled QR estimator with independent LAPACK checks and explicit
hold-out isolation tests. C20 separates order-book and failure seeds, adds
transport trace replay, and uses the physical engine in its timing harness.
See [the corrective report](docs/ARGESIM_CLOSURE_20261120.md) for evidence,
reproduction commands and remaining completion criteria. These corrections
do not change catalog validation gates.

## Transport/data follow-up, 2026-11-19

C20 now implements the individual directed tracks, junctions, buffer slots and
machine locations, with causal blocking, physical source/sink/rework transfers
and corrected Task-B/C statistics. C18 requires an explicit training/validation
pair or an explicitly selected reconstruction demo and records input hashes.
The catalog now has 18 `implemented`, four narrowly `validated` and two
`specified` families: C02 and C18. No family is benchmark-ready.

C02's finite-spacing research candidate is isolated under `experiments`:
zero-storage shifter footprints and the reference mismatch remain open.
Its results do not replace the registered model or its expected failing test.
See [the transport/data report](docs/ARGESIM_TRANSPORT_DATA_20261119.md) and
[its reproducible evidence](docs/BENCHMARK_TRANSPORT_DATA_20261119.json).
The dated sections below retain historical findings; newer corrections
supersede their former open items.

## Corrective follow-up, 2026-11-18

The follow-up implements C04 cleaning/request/conspiracy refinements, C05
sampled trajectories and measured decimal-precision experiments, and C06
individual-doctor service/exchange semantics. These three families now reach
`implemented`; C02, C18 and C20 remain incomplete. The four limited `validated`
labels are unchanged. No family is benchmark-ready.

Additional C02 geometry and timing corrections expose a historical reference
mismatch for ten pallets. Its original 6% threshold is retained as an explicit
expected failure, not counted as successful scientific validation. Repository
Ruff findings are now resolved; two intentional task-failure collection boundaries
are locally annotated. See [the follow-up report](docs/ARGESIM_FOLLOWUP_20261118.md)
for modelling conventions, numerical evidence and remaining limits, and
[the follow-up evidence](docs/BENCHMARK_FOLLOWUP_20261118.json) for actual checks.

## Initial correctness review, 2026-11-18

The following initial findings describe commit
`c57c14aea5fb8d8e5f099db5e898accb7d01bb4a`. Later corrections above supersede
its open items; the per-definition table below records the current state.

**Verdict: the repository does not yet implement every ARGESIM benchmark
correctly and completely.** The audit retrieved the active primary definitions
for all 24 families and compared model assumptions, parameters, event rules,
task entry points and existing tests. It added targeted counterexamples and
independent numerical spot checks. This is not an exhaustive proof, a complete
statistical validation, or a run of all publication-sized workloads.

The starting main commit was `8bc9f2d2a99e591eea9afe257c5a247a8cdffeb9`.
The scheduler correction is commit `2852ab4d0eec8095db1ba8aaddae3edf972d0f3f`
in draft PR #61. The following benchmark fixes build on that correction.
Source URLs and SHA-256 hashes for the 24 definitions, together with numerical
probe results and tolerances, are retained in
[BENCHMARK_AUDIT_20261118.json](docs/BENCHMARK_AUDIT_20261118.json).

### Confirmed defects and corrections

| Case | Counterexample / primary requirement | Correction and remaining limit |
|---|---|---|
| C02 | `solve_c02(50)` and `(60)` returned a hardcoded deadlock before constructing the plant. This was not simulation evidence. | High-load cases now raise `NotImplementedError`; lower-load output reports deadlock as unknown (`None`). Full blocking, merge contention and transport timing remain unresolved. |
| C03 | The supported ideal-switch case `trf=0` and the maximum ramp duration could fail with a minimum-step error. `base+period` and the next `cycle*period` produced an artificial one-ULP interval near 60 us; RK endpoint stages could also sample the next circuit at an ideal switch. | Canonical cycle boundaries, including ramp endpoints coinciding with a cycle edge, and a fixed circuit per ideal-switch segment. Full 100 us ideal-switch trajectory is checked against independent matrix exponentials. |
| C05 | Revised July 1992 Task D requires `c2=-1.25` and return threshold `y1=4.1`. Code used `-2.85` and `2.5`. Switching times/endpoints alone missed the 1.6 state error. | Corrected both parameters and tested all 31 return states. Published 62-event times and final value still pass unchanged. The general solver/tolerance experiment of Task C remains missing. |
| C06 | Definition Task B requires the inexperienced doctor transferred to CW1 to take 20% longer. | Applied the factor only to that doctor's distribution. Alternating aggregate service distributions still do not model persistent individual doctors. |
| C08 | With two eastbound arrivals at t=0, a westbound arrival at t=1 and another eastbound at t=55, the old model admitted three into a cycle limited to two. | Count cumulative admissions separately from remaining occupants. Departure order is now 0,1,2,3 at 54,88,142,196 min. Both directions and incomplete-cycle admission are tested. |
| C09 | Surface generation converted the error axis from cm to m but omitted that conversion for the difference axis. At e=15 cm, de=.0125 cm, IFC2 returned .00008 instead of .000125. | Both axes use the same units as Figure 4. Independently evaluated rule weights check IFC1 and IFC2. |
| C11 | The definition gives `Imax=Tmax/((3/2)*kT)`. Multiplication by 3/2 instead of division allowed 2.25 times the specified motor torque. | Corrected all three current limits. Tests reconstruct joint torque from acceleration for both polarities. |
| C12 | Definition (4) sets all three initial gaps to `a`; code used `(a,0,0)`. It also used Task A1's 15 s plotting horizon for terminal results in A2/B/C. At e=.5 two of six collisions occur after 15 s. | Correct gaps; terminal tasks run until no significant closing velocity remains. Tiny event advances preserve nonoverlap. Elastic events at 1,2,3 s, terminal e=.5 velocities, plastic collapse, momentum and energy are checked. |
| C15 | RK stages straddled the bolus discontinuity. With dose 2500, tau=.5 and RK4 step=.1, x1(1) was 2321.910742 instead of 2403.057754. | Every backend now uses separate bolus-on/off segments, including the left-hand forcing at the first segment's endpoint. Tests include grid-aligned and off-grid bolus durations. |

The initial PR CI also exposed a pre-existing exact floating-point assertion
on Python 3.10/3.11: integrating `y'=1` to `1e-15` differed by one ULP from
the literal. The test now allows two ULPs at that scale; it still rejects zero
or an omitted final interval. This is a portability correction, not a relaxed
scientific accuracy target.

### Open blockers and corrected gates

The strict `implemented` gate requires every required task and model behaviour.
The following six families therefore move back to `specified`, despite useful
partial code. The four retained `validated` labels denote the particular
references listed below, not universal correctness.

| Family | Work still required before claiming complete implementation |
|---|---|
| C02 | Physical belt blocking, shifter/merge priority and pallet occupancy; restore the definition's 2 s shifts at A1/A6 instead of 4/3 s; separate buffer travel from total B1/B2 length and processing travel. The existing 6% throughput proximity check is only historical evidence for the abstraction. |
| C04 | The original open-ended comparison asks for successive refinements: actual dirty/clean chopstick state, cleaning, neighbour request tokens and conspiracy/starvation experiments. Ordered atomic fork acquisition is not the cleaning process. |
| C05 | Sampled y1(t) output and the requested relative-accuracy study across numerical solver settings. The exact event oracle is useful but does not perform that solver experiment. The definition's printed c1=2.7e-6 conflicts with its stiff example; c1=2.7e6 is retained consistently with the published Maple solution and reference events. |
| C06 | Individual doctor identity, service completion and exchange scheduling. Alternation gives equal counts of service starts, which is not equivalent to two servers with different service durations. |
| C18 | Original measured 100 Hz identification/validation data, or an explicitly agreed substitute task. The published-figure reconstruction supports a separate reproducible comparison. |
| C20 | A validated transport topology, junction/buffer occupancy and propagation of downstream blocking. Entry headway in a reduced two-ring abstraction is insufficient evidence for the complete physical conveyor model. |

### Independent numerical spot checks

[benchmark_spec_probe.py](scripts/benchmark_spec_probe.py) uses independently
transcribed equations and NumPy/SciPy, without calling candidate RHS functions
for its references. The audit runtime used NumPy 2.3.5 and SciPy 1.17.0.

| Case | Independent reference | Maximum absolute difference |
|---|---|---:|
| C01, loss=100/1000/10000, 0..10 s | Radau at every candidate trajectory point | 1.51e-8 |
| C03, ideal switch, 20 half-cycle boundaries through 100 us | Affine matrix exponentials | 1.55e-7 |
| C07, both Task-A initial conditions through 10 s | DOP853 with separate pin events and velocity resets | 1.98e-7 |
| C15, all three bolus durations at 240 min | Augmented matrix exponentials for both compartments | 5.23e-12 |

C07 comparisons exclude samples within 1 us of a velocity jump to avoid
comparing opposite sides of a reset. C03's independent check concerns the
ideal-switch limit, not every finite rise/fall-time variant. These probes
do not promote entire families to `validated`.

### Verification of the corrected source

Python 3.12.14 completed **325/325 unit tests**. The complete smoke profile
completed **71/71 tasks across all 24 families**; the three C03 smoke tasks
were repeated successfully after the final coincident ramp/cycle-boundary fix.
All nine independent numerical probes passed. `compileall`, generated status
verification and `git diff --check` passed.

Ruff 0.17.5 still reports **210 pre-existing findings**, with zero new findings
relative to the scheduler commit. The new probe script passes lint and
formatting. Repository-wide CI lint therefore remains blocked by existing
lint debt; successful numerical tests are not an overall green CI claim.
The evidence JSON records commands, results, source hashes and log digests.

Reproduce the checks from the repository root:

```sh
python -m unittest discover -s tests -v
python -m argesim_benchmarks run-suite --profile smoke
python scripts/benchmark_spec_probe.py  # optional NumPy/SciPy audit dependencies
python scripts/update_status_docs.py --check
python -m compileall -q argesim_benchmarks tests scripts
```

## Earlier reviews

The dated sections below retain their original scope. Current family status is listed in [ARGESIM_COVERAGE.md](ARGESIM_COVERAGE.md).

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

## Per-definition result at the 2026-11-18 audit

| ID | Gate | Audit result |
|---|---|---|
| C01 | implemented | Definition equations and parameter study reviewed. Independent Radau spot checks pass at loss=100/1000/10000; every solver/backend is not independently qualified. |
| C02 | specified | Shift/travel/load timing corrected and fabricated deadlocks removed. The 10-pallet published proximity check now explicitly fails; full occupancy, blocking and merge rules remain open. |
| C03 | implemented | Ideal-switch segment and floating-point boundary defects fixed. Independent matrix-exponential check passes through 100 us. Finite-ramp parameter sweeps retain existing tests. |
| C04 | implemented | Atomic/hungry/dirty-cleaning/neighbour-request refinements and reproducible normal, deadlock and two conspiracy policies execute. Timings are declared model choices; no universal fairness proof is claimed. |
| C05 | implemented | Sampled trajectories include fast transients. Tasks C/D measure decimal precision against an 80-digit run; independent 90-digit logarithmic checks cover both parameter sets. This is a semi-analytical backend, not general RK/QSS qualification. |
| C06 | implemented | Persistent doctors replace aggregate alternation. Actual service times, 20% transfer penalty, non-preemptive paired exchange/return, hysteresis and return-visit priority are tested. Handover convention is documented; external statistical validation remains open. |
| C07 | implemented | Pin mode equations and velocity resets reviewed. Both Task-A cases pass independent DOP853 spot checks; Task-C published initial-velocity check remains. |
| C08 | validated | Cumulative cycle admission bug fixed in both directions. Five deterministic appendix datasets and replication/interval checks pass; stochastic output is not a universal distributional validation. |
| C09 | implemented | IFC surface difference-axis units fixed. Rule-weight regression and full sampled scenario checks pass. Reference level-change versus literal error-difference ambiguity remains explicitly selectable. |
| C10 | implemented | Left-before-right acquisition, simultaneous-access priority, deadlock termination and 50-run task reviewed. Tests check these rules; full published trace comparison remains open. |
| C11 | implemented | All motor current limits corrected from 2.25x excess. Inertia and explicit equations reviewed; task and torque-limit tests pass. Collision safety between samples and every solver remain unqualified. |
| C12 | implemented | Equal initial gaps and terminal collision horizon corrected. Elastic times, late impacts, momentum, dissipated energy and plastic collapse tested. Boundary-value/stochastic tasks rerun. |
| C13 | implemented | Revised d_l=.001, sampled controller and disturbance cases reviewed. Existing revision analysis distinguishes 2006 d_l=.01 reference values; no complete independent revised closed-loop validation. |
| C14 | implemented | Factory/product tables, lead times, initial fill, wholesaler rules and daily order strategies reviewed. Tests verify those rules; full 100-run statistical reference comparison remains open. |
| C15 | implemented | Bolus switching now segmented for all backends. Independent matrix-exponential endpoint checks pass; identification/Monte Carlo and published parameter checks retain existing coverage. |
| C16 | implemented | Population/location rules, weekly accounting, distance density and task entry points reviewed. Deterministic boundary tests pass; full 50-replication multiyear statistical qualification not run in this audit. |
| C17R | implemented | Revised ODE identification, FHP-I exclusion/collisions, random movement and intervention paths reviewed. Conservation/replay tests pass; ensemble agreement and spatial parameter regions require further numerical validation. |
| C18 | specified | ARX and both ANN forms execute on labelled digitizations or supplied data. Original 100 Hz data missing; synthetic recovery and figure correlations cannot certify the original experiment. |
| C19R | implemented | Transport/source/facility equations and 150-day task horizons reviewed. Full mesh-convergence and prescribed section/profile error evidence remain open; coarse-grid smoke tests are not PDE validation. |
| C20 | implemented | Directed Figure-4/5 geometry, finite occupancy and downstream blocking now coupled to production. All 12 scenarios and a 5,000-order run execute; aggregate independent validation and the full 120-replication study remain unperformed. |
| C21 | validated | Existing published ball/pendulum event and dynamic-contact checks pass; diode forms have residual/cross-form tests. This is limited reference validation, not arbitrary DAE or every parameter combination. |
| C22 | implemented | Queue choice, event priority, reneging, jockeying and class-call rules reviewed. Existing deterministic trace/length tests pass; independent complete published traces remain open. |
| CP1 | validated | Task-B published ten-population endpoint and equilibrium checks retained. Serial/parallel equality is verification, not independent validation of all workloads or speedup. |
| CP2 | validated | Corrected rope/Fourier and reference LBM algorithm checks retained. Full 257x257, 350000-iteration cavity workload and publication-scale parallel performance were not rerun in this audit. |

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
- C20 now encodes the drawing's tracks, junctions and buffer slots. Its
  conservative documented controller is not an optimized or independently
  validated reference solution; a full 120-replication study is still absent.
- C18 reports teacher-forced and free-running dynamic-ANN metrics separately;
  the former is not presented as closed-loop simulation evidence.
- No general-purpose implicit DAE solver is claimed. Quantized partitions are
  limited to autonomous ODEs; the full BDF partition may be non-autonomous.
