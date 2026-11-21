# C20 transport and C18 input-data review, 2026-11-19

This record describes the conveyor layout, controller and input contract
introduced in the November 19 review. Its hashes and numerical results
identify that revision. The subsequent C20 study exercised all 12 scenarios
with three order books. [November 19 evidence](BENCHMARK_TRANSPORT_DATA_20261119.json) ·
[Full C20 study](ARGESIM_CLOSURE_20261120.md#c20-fixed-book-experiment-and-replay)

## C20 model and task corrections

The old area-level ring calculator reserved entire future trips on request,
freed transport capacity without downstream acceptance and omitted the actual
junctions/buffer slots. Its documentation now labels it a legacy approximation.
Explicit `transport_time` retains the reduced fixed-delay experiment; the
default uses `C20Layout`, `C20Flow` and `C20Production`.

| Requirement | Implementation |
|---|---|
| Directed geometry | 284 nodes, 368 tracks; specified straight lengths and arc lengths |
| Central failure clusters | 36 whole tracks: A=16, B=8, C=12; processing-area tracks excluded |
| Machines | 19 machines at Table-1 area.slot positions; unused positions closed |
| Capacity and blocking | One part per junction; FIFO belts retain occupants until downstream accepts; capacity floor(length/1 m), speed 1 m/s, headway 1 s |
| Storage | 90 slots in 30 FIFO columns, with reservations preventing overbooking and out-of-order admission |
| Setup | Workstation admission stays closed throughout tool/operation changes |
| Time constraints | MIN=600 s, MAX NOK=360 s, MAX OK=300 s, checked at actual process start |
| NOK/rework | Physical discharge/replacement through area 0, or physical repeat of O6 for MAX OK |
| Completion | Final transport to sink included; throughput time begins at earliest release |
| PSc4 | Seeded gamma disruptions, one failed central track at a time, 600 s repairs and paused in-flight motion |
| Task B | Median/IQR of individual order throughput times pooled across runs; distribution of run medians retained separately |
| Task C | Unweighted and weighted total tardiness, plus tardy-order count |

The source-to-area-1/WS1 trip is independently checked against
`183 + 9.5*pi = 212.8451302091 m` and the same duration at 1 m/s.
A blocked two-belt fixture fills the belts/junctions and blocks the source,
then drains without loss or overtaking. A failure at t=1 adds its exact
five-second pause to an otherwise four-second journey. Tests also cover
300/360-second boundaries, empty setup, FIFO reservations and 600-second
cooling.

### Declared controller and conventions

The controller admits at most 30 active parts by default (`wip_limit`).
Released orders are prioritized by rush flag (OSc2/3 only), due date and
identifier; the nearest idle eligible machine is selected. It does not use
future order knowledge. Waiting parts use the nearest accessible FIFO buffer.
A later column reservation is admitted only after the earlier incoming part
arrives. Outgoing reservations remain until their journeys finish. This
conservative rule affects performance but prevents reservation overtaking.

Routes are directed shortest paths avoiding currently failed tracks when an
alternative exists. Later failures on a chosen route are waited out. The
controller is not optimized. Default bypass edges remain available for
journeys that do not enter a workstation/storage column. Machines remain
busy until the completed part actually departs. Conveyor gamma uptime starts
after the previous repair, preserving one simultaneous disruption.

Transport delay fields are diagnostics: the failure field sums pauses of parts
on broken belts; the remaining delay includes capacity and admission waits.
They do not causally separate indirect failure effects. A 24-hour simulated
no-progress watchdog and an event cap fail explicitly; a watchdog failure is
not labelled a proven physical deadlock.

### Execution evidence and limits

All 12 OSc/PSc combinations completed 100 orders with seed 20. A full
5,000-order OSc3/PSc4 run, seed 20, completed with 96 conveyor disruptions,
153 MAX NOK and 507 MAX OK violations. Makespan was 400485.118817556 s;
median order throughput was 178402.243297098 s. These are observations of
the declared controller, not published reference values.

The later study completed 360 definition-sized runs with three generated
books. The physical model remains at `implemented` pending a comparison
with matched external inputs and controller rules. [Study results](C20_EXPERIMENT_20261120.json)

## C18 explicit data contract

Supply both training and validation datasets or CSV paths to `run_c18_tasks`,
or explicitly select `use_digitized=True`.
A single supplied dataset is never combined with a default substitute.
Sampling rates must match; digitized and supplied source kinds cannot be
mixed. Data values are copied into immutable tuples.

`load_c18_csv` requires `time_s,thickening,force` columns (any order), finite
values and uniform monotone times, at 100 Hz by default. Missing samples are
not interpolated. Optional `expected_sha256` pins input bytes. Results retain
both datasets' provenance, sample counts/rates, signal hashes and file hashes.
Checksums establish identity, not original ARGESIM-data authenticity.

```sh
python -m argesim_benchmarks run C18 all --kwargs-json '{"training":"training.csv","validation":"validation.csv"}'
python -m argesim_benchmarks run C18 all --kwargs-json '{"use_digitized":true,"epochs":2}'
```

Smoke explicitly uses the reconstruction demo. The definition profile reports
the missing-data error. The original 100 Hz training/validation files were
not recovered from the checked active ARGESIM/SNE pages. That remains the
blocker for the original experiment.

## C02 prototype

The separate spatial C02 prototype and its six-run evidence belong to this
dated snapshot. The registered C02 solver now uses finite storage, shifter
reservations and physical deadlock detection. [Current C02 implementation](C02_IMPLEMENTATION.md)

[C20 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_21_34/articles/sne.21.34.10097.bn20.OA.pdf),
[C18 definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C18/C18-definition.pdf),
[C02 definition and clarifications](https://www.sne-journal.org/benchmarks/c02).
