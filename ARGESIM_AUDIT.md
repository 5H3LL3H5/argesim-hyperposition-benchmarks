# ARGESIM implementation audit

The [catalog](argesim_benchmarks/catalog.py) assigns evidence levels to the 24 families. The [coverage tables](ARGESIM_COVERAGE.md) pair those levels with the tasks exported by the runner. The [reference comparison](docs/PUBLISHED_REFERENCE_CHECKS.md) records which cases meet an independent numerical or statistical criterion.

## Where the evidence stops

| Family | Reproduced result | Evidence still needed |
|---|---|---|
| C02 | The default finite conveyor admits all loads from 1 to 60. Loads 50–60 deadlock. Nine of twelve quantitative SimEvents rows pass for both throughput and mean part time. | At 13 and 14 pallets both default measures miss the 6% band. At 25 the mean misses. Timer edges, initial positions and the original SimEvents model would allow a matched comparison. [Pallet study](docs/C02_IMPLEMENTATION.md) |
| C09 | The default P-FC plateau before the disturbance matches Figure 9. A replay driven by the published valve trace reproduces the I-FC2 peak under the documented scale convention. | The registered closed loop misses that peak and the post-disturbance P-FC plateau. The original controller and signal scaling would distinguish the causes. [Windows and tolerances](docs/C09_FIGURE_CHECKS.md) |
| C11 | The nine-state implementation limits armature currents at accepted samples, restarts from the bounded state and carries the remaining solver budget across restarts. | A matched independent controller trajectory and an inter-sample collision check. [Model](argesim_benchmarks/models/c11_scara_robot.py) · [Regressions](tests/test_argesim_c11.py) |
| C13 | Revised linear Task A meets its endpoint tolerance for all three loads. The stationary brake test engages at 3.1 s with the 0.1 s sampling period. | Independent trajectories for the revised nonlinear and controlled cases. [Crane analysis](docs/C13_REFERENCE_ANALYSIS.md) |
| C16 | The mean restaurant count at week 260 meets the declared comparison with both AnyLogic and Java. | The local sample has lower variance. The economic studies use different observation windows and revenue measures. [Restaurant results](docs/C16_VALIDATION.md) |
| C17R | The default deterministic trajectories agree with an independent scalar reference. The spatial study compares 32 seeded runs with one published scalar. | Independent spatial fields and intervention scenarios. [ODE and spatial results](docs/PUBLISHED_REFERENCE_CHECKS.md#c17r-default-ode-and-spatial-comparison) |
| C18 | ARX and both neural models run on supplied data or on four explicitly reconstructed figure traces. | Both original 100 Hz recordings are needed for the official identification and held-out experiment. [Data and fit results](docs/C18_FIGURE_RECONSTRUCTION.md) |
| C19R | Homogeneous reference profiles and a local grid-refinement study quantify spatial error. | Breakthrough at 50 m and the treatment disks retain significant grid error. [Profiles and grid study](docs/PUBLISHED_REFERENCE_CHECKS.md#c19r-spatial-and-time-accuracy) |
| C20 | Three generated order books produced 360 complete runs. Independent replay checked 36 traces with 55,648,862 events. | External output parity requires the original books and comparable dispatch and reservation rules. [Experiment](docs/ARGESIM_CLOSURE_20261120.md) |

The same comparison covers the outstanding C04 fairness distributions, C10 deadlock and wait distributions, and C14 ordering-policy differences. [Remaining families](docs/PUBLISHED_REFERENCE_CHECKS.md#remaining-families)

## Traceability

The original 24-definition audit retained primary-source URLs, document hashes, numerical probes and the code revision it inspected. The dated follow-ups preserve the test parameters, source hashes and findings for their respective revisions. [Initial evidence](docs/BENCHMARK_AUDIT_20261118.json) · [Dated results](docs/README.md#dated-results)

To check the current tables without writing files, run the catalog tests. To regenerate both tables after a catalog, registry or evidence-note change, use the update script.

```sh
python -m unittest discover -s tests -p test_argesim_catalog.py -v
python scripts/update_status_docs.py
```
