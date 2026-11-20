# C02, C18 and C20 corrective follow-up

This follow-up starts from merged main commit
`be8746ef67380fe930c6896374bca8066c9b2b94`. It fixes additional reproducible
implementation defects and expands the verification evidence. It does not
declare the three benchmark families fully validated.

## C02 routing and simultaneous arrivals

Initially empty pallets now bypass assembly stations until A1 loads them.
A2 is permitted only before or after the whole A3/A4/A5 group; it cannot
interrupt a partially completed group. Admission now reserves a branch slot
when the router makes its decision, before the next DEVS microstep delivers
the message. Multiple arrivals therefore cannot all claim the same slot.

These are corrections to the existing partial model. Finite B1 blocking,
zero-storage shifter footprints, adjacent Sy/Sx handoffs and physical
deadlock detection remain incomplete. The registered model continues to
reject 50/60-pallet cases and reports `deadlock: null` for lower loads.
The existing ten-pallet reference failure remains explicit; its 6% threshold
has not been widened. The spatial research candidate remains unregistered.

Reference comparisons also need a matched controller and timing convention.
The 2011 SimEvents solution routes to the first eligible branch with room.
The registered abstraction uses load balancing among A2 stations and an A6
preference heuristic. The 2024 Warteschlangensimulator paper uses such
heuristics but models B1 as unbounded delay stations and measures six hours
after warm-up, whereas the original task measures eight hours after warm-up.
Neither paper's aggregate table by itself certifies full physical conformance
of this repository's abstraction. No travel time, processing time or reference
tolerance was tuned to force a match.

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

The timing harness in `benchmarks/benchmark_argesim_c20.py` now calls the
registered physical production model. It previously used the old five-second
transport demonstration and an obsolete processing-time call signature.

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

```sh
python scripts/c20_experiment.py --workers 6 \
  --checkpoints /tmp/c20-study \
  --output c20-study.json
python benchmarks/benchmark_argesim_c20.py \
  --repeat 1 --warmup 0 --orders 5 --plant PSc1
```

Checkpoints pin the source files and protocol; resuming with stale inputs is
rejected. The report records every run's metrics, deterministic result hash,
input-book hash, replay counts and source hashes. Generated books are not
renamed to the unavailable published OB1000/OB1001/OB1002 files. The published
FlexSim controller uses reservation scheduling, whereas this repository uses
rush/due-date dispatch with a 30-part WIP bound. Its numerical table is
therefore not an exact acceptance oracle for this controller.

## Remaining completion criteria

| Family | Remaining requirement |
|---|---|
| C02 | Complete finite transport and zero-storage shifter model; matched controller/initial-state experiments including 60 pallets. |
| C18 | Recover both authentic measured data sets and run the identification/validation experiment on them. |
| C20 | Independent verification of full geometry and workstation semantics, plus comparable external experiments with matched books and controller. |

Catalog statuses remain unchanged: C02/C18 `specified`, C20 `implemented`.
The numerical and trace checks do not promote whole families to `validated`
or `benchmark-ready`.

## Primary references

- [C02 definition and clarifications](https://www.sne-journal.org/benchmarks/c02).
- [Pingel and Pawletta, SimEvents C02 solution, 2011](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_21_34/articles/sne.21.34.10101.bn02.OA.pdf).
- [Herzog, C02 modelling study, 2024](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_34_1/articles/sne.34.1.10673.bn02.OA.pdf).
- [C18 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-definition.pdf).
- [C18 Excel solution, including the published linear transfer function](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-solution-Excel.pdf).
- [C20 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_21_34/articles/sne.21.34.10097.bn20.OA.pdf).
- [Schulz et al., FlexSim C20 solution, 2012](https://www.argesim.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_22_1/articles/sne.22.1.10119.bn20.OA.pdf).
