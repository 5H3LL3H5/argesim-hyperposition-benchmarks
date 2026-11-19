# C02 implementation limits

C02 remains **specified**, not implemented or validated. The registered
`solve_c02` path is a partial transport abstraction: `deadlock` is `None`,
and 50/60-pallet cases raise `NotImplementedError`. Its ten-pallet result
fails the retained 6% reference check, explicitly marked as an expected
failure. The 14/20/40-pallet checks remain active but do not prove physical
conformance.

The previous document claimed full geometry/routing and a simulated high-load
deadlock, and listed obsolete outputs. Those claims were incorrect and are
withdrawn.

## Spatial candidate, 2026-11-19

`argesim_benchmarks.experiments.c02_spatial.C02SpatialCandidate` is an isolated
research candidate. It uses integer-centimetre pallet positions, event-driven
motion, finite station buffers, single positioning units, reserved shifts
and B2 merge precedence. Routing takes the first required operation with room;
A2 is not interleaved with a partial A3/A4/A5 group. A6 completes the missing
operations together. Empty pallets start equally spaced unless explicit
nonoverlapping positions are supplied.

**Known gap:** its point representation of the shifters does not enforce the
complete zero-storage footprints, especially at the two adjacent Sy/Sx pairs.
Spacing and finite B2 storage alone do not establish this requirement. The
candidate is therefore not registered and does not replace `solve_c02`.

Exploratory 600-minute runs, with 120-minute warm-up:

| Pallets | Published throughput | Candidate throughput | Published mean (s) | Candidate mean (s) |
|---:|---:|---:|---:|---:|
| 10 | 959 | 921 | 285 | 305.1422 |
| 14 | 1439 | 1278 | 265 | 307.9667 |
| 20 | 1439 | 1382 | 385 | 409.2893 |
| 40 | 1437 | 1381 | 787 | 826.2012 |
| 50 | deadlock | 1381 | — | 1036.4256 |
| 60 | deadlock | 1384 | — | 1245.2925 |

All six candidate runs retained at least 0.36 m centre spacing and respected
the 3/2-pallet input-buffer and one-pallet output-buffer bounds. Mean time is
measured from completed loading to completed unloading. None deadlocked.
These observations are **not corrected reference values or C02 validation**.
Control and initial-position details also matter to comparison; no timing
constant or tolerance was adjusted to fit the table.

Acceptance still requires full shifter-footprint/no-buffer semantics,
zero-gap handoff tests, a traceable match of control and initial conditions,
and comparisons covering every definition load, including 60 pallets.

Sources: [1991 definition and clarifications](https://www.sne-journal.org/benchmarks/c02),
[2011 independent SimEvents solution, Table 2](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_21_34/articles/sne.21.34.10101.bn02.OA.pdf).
