# C18 numerical verification and C20 production study, 2026-11-20

The November 20 follow-up to `be8746ef` recorded independent C18 estimator
checks and a C20 production and transport replay study. Its C02 routing work
used the earlier partial plant. The current finite-conveyor study covers loads
1–60 and documents the three remaining default SimEvents discrepancies.
[C02 reference and reproduction](C02_IMPLEMENTATION.md)

## C18 numerical identification

The ARX fit now uses column-scaled Householder QR. The previous normal-equation
solver squared the design matrix's condition number and used an absolute
pivot threshold; a perfectly identifiable system expressed in small units
could be rejected as singular. The QR estimator preserves the original
least-squares objective and ridge penalty by augmenting the observations
with `sqrt(ridge) * I` before scaling columns.

Tests recover a known ARX system at signal scales `1e-12`, `1` and `1e12`,
check rank deficiency and regularization, and mutate held-out force samples
to verify that they do not change trained models or free-run predictions.
One-step predictions intentionally use measured past outputs and are checked
separately. Non-finite training inputs, learning rates and metric inputs are
rejected instead of silently producing NaN results.

[C18_NUMERICAL_CHECKS_20261120.json](C18_NUMERICAL_CHECKS_20261120.json) contains
six comparisons with NumPy/LAPACK on a noisy synthetic system, with and without
regularization at all three scales. The independent estimator agreement is
numerical verification, not validation on the original muscle measurements.

The two original 100 Hz measurement sets remain unavailable in the sources
checked. The active definition and solution pages provide descriptions and
papers, but no recovered measurement download. Figure reconstructions remain
explicit demos. Their provenance is not changed to measured data.

```sh
python scripts/c18_numerical_probe.py --output c18-checks.json
```

The optional probe requires NumPy. The production estimator has no external
runtime dependency.

## C20 fixed-book experiment and replay

`order_seed` now separates generated order books from failure realizations.
`run_c20_experiment` holds one book fixed across replications. The standalone
study runs several books, records their byte-identical input hashes across
replications, and calculates Task B from pooled individual-order observations.
Per-replication medians remain a separate statistic.

The timing harness uses the registered physical production model. [Timing script](../benchmarks/benchmark_argesim_c20.py)

Transport now visits occupied/requested tracks instead of scanning the entire
layout on every event. Layout order is retained for simultaneous events.
Eligible machines are cached, and intermediate conveyor crossings only
dispatch when they can enable source admission; machine, buffer and process
events retain their explicit dispatch callbacks.

Differential checks against the pre-change model compared complete results,
including every order and transport aggregate: all twelve 100-order scenarios
(seed 21) and the 5,000-order OSc3/PSc4 run (seed 20) were exactly equal. The
latter took approximately 26 s instead of 127 s on this audit machine. These
are local timing observations, not cross-platform performance guarantees.

The independent replay implementation does not call the simulator's routing,
dispatch or conservation methods. It replays insertions, removals and track
events, checking ownership, FIFO order, finite capacity, one-second headways,
failure pauses, transport speed and agreement with reported trip paths.
Deliberately corrupted metrics, occupancies, identities, paths and truncated
traces must fail its tests. The replay uses the supplied layout and does not
independently certify the drawing's transcription or workstation physics.

The full protocol is three generated books (seeds 20, 21, 22), all twelve
OSc/PSc combinations, ten failure realizations (seeds 1000–1009) and 5,000
orders per run: 360 runs / 1.8 million completed orders. Every run undergoes
independent metric recomputation; the first replication of each book/scenario
also undergoes full transport replay (36 complete traces).

All **360 runs / 1,800,000 completed orders** passed. The 36 replay checks
covered **55,648,862 trace events and 1,263,763 completed transport trips**
without a violation of the replayed rules. Observed WIP and buffer reservations
both peaked at 30. Each deterministic PSc1 group had zero makespan IQR across
its ten replications. The complete per-run metrics, all 36 scenario/book
summaries and source identities are in
[C20_EXPERIMENT_20261120.json](C20_EXPERIMENT_20261120.json).

```sh
python scripts/c20_experiment.py --workers 6 \
  --checkpoints /tmp/c20-study \
  --output c20-study.json
python benchmarks/benchmark_argesim_c20.py \
  --repeat 1 --warmup 0 --orders 5 --plant PSc1
```

Checkpoints pin the source files, protocol and Python implementation/version;
resuming with stale inputs or another runtime is rejected. The report records
every run's metrics, deterministic result hash,
input-book hash, replay counts and source hashes. Generated books are not
renamed to the unavailable published OB1000/OB1001/OB1002 files. The published
FlexSim controller uses reservation scheduling, whereas this repository uses
rush/due-date dispatch with a 30-part WIP bound. Its numerical table is
therefore not an exact acceptance oracle for this controller.

The study's recorded source hashes identify the code in commit
`48dc0b2499ea2a6e45a9298999c1ee2c93063a39`.

## Reuse of the recorded evidence

The November 20 LAPACK comparison checks the ARX estimator. The current C18
demo uses 2,000 figure-derived samples per signal and output-feedback training.
Its held-out results and missing official recordings are documented separately.
[C18 figure study](C18_FIGURE_RECONSTRUCTION.md)

The C20 report pins the five production, layout, flow, model and replay source
files plus the study driver. The five model/replay hashes match the reviewed
implementation. The driver fingerprint differs after checkpoint validation
was tightened. Compare protocol, per-run metrics and result hashes when
reproducing the experiment. [Study driver](../scripts/c20_experiment.py) ·
[Archived protocol and results](C20_EXPERIMENT_20261120.json)

## Primary references

- [C02 definition and clarifications](https://www.sne-journal.org/benchmarks/c02).
- [Pingel and Pawletta, SimEvents C02 solution, 2011](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_21_34/articles/sne.21.34.10101.bn02.OA.pdf).
- [Herzog, C02 modelling study, 2024](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_34_1/articles/sne.34.1.10673.bn02.OA.pdf).
- [C18 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-definition.pdf).
- [C18 Excel solution, including the published linear transfer function](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-solution-Excel.pdf).
- [C20 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_21_34/articles/sne.21.34.10097.bn20.OA.pdf).
- [Schulz et al., FlexSim C20 solution, 2012](https://www.argesim.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_22_1/articles/sne.22.1.10119.bn20.OA.pdf).
