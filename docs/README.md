# Documentation

Use the [coverage table](../ARGESIM_COVERAGE.md) to find a family, its registered task names and its evidence level. The [reference comparisons](PUBLISHED_REFERENCE_CHECKS.md) identify the tested observable, tolerance or statistical criterion and outstanding differences for all 24 families. Commands in these documents run from the repository root.

## Model reports

| Family | Report |
|---|---|
| C01 | [Lithium-cluster trajectories, equilibria and Task A timing protocol](C01_RESULTS.md) |
| C02 | [Pallet routing, timer conventions and the SimEvents, CSIM and AnyLogic comparisons](C02_IMPLEMENTATION.md) |
| C03 | [Switch-state eigenvalues and ideal and finite-ramp references](C03_VALIDATION_REPORT.md) |
| C06 | [STROBOSCOPE daily patient and closing-time statistics](PUBLISHED_REFERENCE_CHECKS.md#c06-replicated-comparison) |
| C08 | [Five deterministic canal-and-lock datasets](C08_VALIDATION.md) |
| C09 | [Digitized Simulink levels and valve-trace replay](C09_FIGURE_CHECKS.md) |
| C13 | [Crane revision history, independent linear reference and sampled braking](C13_REFERENCE_ANALYSIS.md) |
| C14 | [Supply-chain ordering conventions and D1 costs](C14_VALIDATION.md) |
| C16 | [Week-260 statistical validation](C16_VALIDATION.md) and [dining and weekly accounting transitions](C16_DEVS_SPECIFICATION.md) |
| C17R | [Deterministic ODE references and the spatial single-run comparison](PUBLISHED_REFERENCE_CHECKS.md#c17r-default-ode-and-spatial-comparison) |
| C18 | [Identification inputs, figure reconstruction and held-out results](C18_FIGURE_RECONSTRUCTION.md) |
| C19R | [Temporal and spatial accuracy of groundwater profiles](PUBLISHED_REFERENCE_CHECKS.md#c19r-spatial-and-time-accuracy) |
| C20 | [Production topology and controller](ARGESIM_TRANSPORT_DATA_20261119.md) and [360-run study with independent replay](ARGESIM_CLOSURE_20261120.md) |

## Runtime and verification

- [From DEVS to QSS](QSS_DEVS_HISTORY.md) traces the origins, works through an interrupted quantizer and compares explicit RK23 and stiff ESDIRK32 with reference solutions.
- [Solver selection](SOLVER_SELECTION.md) compares QSS and classical solvers by problem structure and common accuracy targets. The [PDF](ARGESIM_SOLVER_STUDY.pdf) includes the history, selection study, foundations and eight-case report.
- [Earlier solver comparison](SOLVER_COMPARISON.md) reports 456 configurations, the C21 event repair and the independent diode results. The [methods appendix](SOLVER_METHODS.md) explains each solver.
- [Methodology](../METHODOLOGY.md) covers execution evidence, diagnostic timing, superdense event ordering and independent validation.
- [Solver guide](../QSS_SOLVERS.md) gives runtime names, model assumptions, Jacobian options and examples. The [QSS method comparison](../QSS_STATE_OF_THE_ART.md) includes an event-count experiment.
- [CIFASIS adapter](CIFASIS_ORACLE.md) describes the optional native scalar-decay pilot, installation, output contract and pinned engine.
- [Implementation audit](../ARGESIM_AUDIT.md) connects current evidence gaps to the relevant reports and source records.

## Dated results

| Date | What the record measures |
|---|---|
| 2026-09-28 | [Local baseline on its identified Git tree](BASELINE_2026-09-28.md) and [RK45 tolerances, endpoint handling and derivative reuse](SOLVER_REVIEW_2026-09-28.md) |
| 2026-11-18 | [Definition sources and independent probes](BENCHMARK_AUDIT_20261118.json) and [C04–C06 model refinements](ARGESIM_FOLLOWUP_20261118.md) |
| 2026-11-19 | [C20 layout checks and C18 input contract](ARGESIM_TRANSPORT_DATA_20261119.md) |
| 2026-11-20 | [C18 estimator and C20 replay evidence](ARGESIM_CLOSURE_20261120.md) and [C02 default 1–60 pallet study](C02_PALLET_STUDY_20261120.json) |
