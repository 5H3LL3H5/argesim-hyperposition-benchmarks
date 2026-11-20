# C02 flexible assembly system

The registered C02 solver simulates the eight-station plant and its pallet
study with finite conveyor storage. For the definition's 20 and 40 pallets it
produces 1,409 and 1,411 parts in eight hours. At 60 pallets it reaches a
physical deadlock after 886.17 s. Nine of the twelve quantitative SimEvents
cases meet the repository's 6% band for both measures. The catalog status
is `implemented`.

## Transport and control

A B1 segment holds five complete 0.36 m pallets at A1/A6 and four at each
other station. B2 has an input buffer (three or two pallets respectively),
a 0.4 m positioning unit and a one-pallet output buffer. Six 0.4 m connectors
each hold one pallet. At 18 m/min the plant advances to transport, clearance
or service events on a lattice of 1/30 s. FIFO admissions and departures are
separated by at least one pallet pitch. The positioning unit handles approach,
service and clearance in sequence and can remain blocked by its output.

Every straight shifter crossing takes 0.4 m / 0.3 m/s = 4/3 s. A lateral
transfer adds 2 s to that travel, taking 10/3 s. A pallet reserves a
downstream slot before entering a shifter. At A2_3→A3 and A6→A1 it reserves
the two contiguous Sy/Sx crossing intervals and the final B1 or B2 space
together. If both arrivals are admissible at Sy, the B2 return has priority.

One A2 policy is selected for the entire experiment.

| `controller` | A2 dispatch |
|---|---|
| `first-eligible` (default) | Take the first eligible A2 with available input space, following the published SimEvents A2 listing. |
| `cyclic-a2` | A2_1 selects every third passage, A2_2 every second and A2_3 every passage, subject to eligibility and space. Each actual passage advances the station counter once, including bypasses. |

A2 can run before or after the complete A3/A4/A5 group. Both controllers
use the A3 decision in Herzog's executable model. A3 accepts work if at least
two pallets occupy A6's input belt and positioning/processing unit combined.
The threshold in the 2024 article's prose is three. Its model file tests two.
Pending shifter arrivals and the A6 output buffer do not contribute. A4/A5
require the preceding group operations. A6 completes the remaining group in
one 30 s service. The document and model links below identify the sources of
these choices.

## Startup and clocks

Empty pallets are placed at evenly spaced indices among the 40 legal resting
places on B1 and its connectors. Larger populations start with 40 on B1.
Surplus pallets enter at A1 as space clears, yielding to circulating traffic.
This makes Pllana and Fahringer's observation about the limited initial B1
space reproducible. In the standard 1–60 study all pallets enter by 734.17 s.
The run reports how many were initially on B1, how many are still waiting
and when the last pallet entered. A deadlock report includes the inventory
in the staging queue when it is occupied.

Throughput counts completed unloadings from 7,200 through 36,000 s inclusive.
The timestamp of a part loaded before the window carries over. Each mean is
for the same measured completions. With zero completions the means are null.

| Field | Start at A1 | End at A1 |
|---|---|---|
| `average_throughput_time` (s) | Loading complete | Unloading starts |
| `average_to_unload_complete_seconds` | Loading complete | Unloading complete |
| `average_including_handling_seconds` | Loading starts | Unloading complete |

For one pallet, 13.6 m of subsystem belts, 2.4 m of connectors and 6.4 m
of shifters give 74.6667 s of forward travel. Six lateral shifts add 12 s,
A2 and A6 add 90 s, and A1 handling adds 15 s. The part-time mean is 176.6667 s
and the full cycle is 191.6667 s. The standard window contains 150 parts,
matching the single-pallet AnyLogic reference and Herzog's analytical time.

## SimEvents comparison

The table uses `first-eligible` and the loading-complete to unloading-start
clock for every row. Pingel and Pawletta describe A2 and the A1 timer but
supply neither per-workpiece timestamps nor the complete A3–A6 controller
and initial placement in the article.

| Pallets | Published count | Model count | Difference | Published mean (s) | Model mean (s) | Difference |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 959 | 939 | -2.09% | 285 | 291.68 | +2.35% |
| 11 | 1072 | 1043 | -2.71% | 280 | 288.65 | +3.09% |
| 12 | 1185 | 1126 | -4.98% | 276 | 291.61 | +5.66% |
| 13 | 1298 | 1220 | -6.01% | 273 | 291.57 | +6.80% |
| 14 | 1439 | 1331 | -7.51% | 265 | 288.05 | +8.70% |
| 15 | 1439 | 1409 | -2.08% | 285 | 291.67 | +2.34% |
| 20 | 1439 | 1409 | -2.08% | 385 | 393.83 | +2.29% |
| 25 | 1439 | 1409 | -2.08% | 396 | 496.47 | +25.37% |
| 30 | 1440 | 1408 | -2.22% | 586 | 600.27 | +2.44% |
| 35 | 1438 | 1409 | -2.02% | 682 | 699.15 | +2.51% |
| 40 | 1437 | 1411 | -1.81% | 787 | 801.20 | +1.80% |
| 45 | 1440 | 1409 | -2.15% | 882 | 901.94 | +2.26% |

At 13 and 14 pallets both measures exceed the 6% tolerance. At 25 the mean
exceeds it. These three numeric comparisons are explicit expected failures.
Their model execution, admission, clock consistency and the 25-pallet
throughput are checked independently. The 2003 CSIM study reports 499.33 s
at 25 pallets. SimEvents reports 396 s. The difference between the published
results remains unresolved.

The default controller runs to the horizon at every population from 1 to 49.
All loads from 50 to 60 are fully admitted before the plant stops. At 50 the
last movement finishes at 3,412.17 s and at 60 at 886.17 s. The terminal
wait-for graph records every occupied resource and its full downstream
blockers. The event scheduler also checks outstanding motion and service.

The study ranks fully admitted, productive runs first by measured throughput,
then by shortest mean part time and finally by fewest pallets. Under this
rule 40 pallets produce the highest count (1,411, mean 801.20 s). Already
at 15 pallets the plant produces 1,409 (291.67 s). Three A2 units with
60 s of work and 4/3 s of positioning each have a combined nominal rate of
1,408.70 parts per eight hours. Completions close to the window boundaries
affect the integer count.

The study also executes SimEvents Listing 3 on its published range of 10–49.
It minimizes `abs(throughput - mean_seconds) * throughput`. On the default
simulation the minimum is 587,559 at 49 pallets. On the paper's own Table 2,
10 pallets score 646,366 and 14 score 1,689,386. Thus 14 cannot minimize the
printed expression even on the paper's data. The article reports 14. Resolving
which objective or input data produced that claim requires further source
material. Shorter studies explicitly report how many eligible loads they score.

## Cyclic A2 comparison

The cyclic policy uses the same transport, A6 rule, startup and observation
window. Breitenecker and Kittenberger publish the following AnyLogic counts
and full-cycle times. The model cycle column uses the solver's full-cycle clock.
All productive rows meet the same 6% band on both measures except at nine
pallets. Both models reach gridlock at 50.

| Pallets | Published count | Model count | Published cycle (s) | Model cycle (s) |
|---:|---:|---:|---:|---:|
| 1 | 150 | 150 | 191.67 | 191.67 |
| 3 | 451 | 451 | 191.67 | 191.67 |
| 5 | 698 | 683 | 206.41 | 210.85 |
| 7 | 964 | 915 | 209.09 | 220.27 |
| 9 | 1214 | 1124 | 213.50 | 230.58 |
| 11 | 1394 | 1346 | 227.34 | 235.28 |
| 12 | 1409 | 1409 | 245.32 | 245.37 |
| 13 | 1409 | 1409 | 265.76 | 265.77 |
| 20 | 1409 | 1408 | 408.67 | 408.90 |
| 40 | 1409 | 1408 | 819.26 | 813.35 |
| 49 | 1409 | 1408 | 1003.90 | 999.27 |

## Reproduction

The default study is [archived as CLI output](docs/C02_PALLET_STUDY_20261120.json).

```sh
python -m argesim_benchmarks run C02 main --kwargs-json '{"num_pallets":60}'
python -m argesim_benchmarks run C02 main --kwargs-json '{"num_pallets":12,"controller":"cyclic-a2"}'
python -m argesim_benchmarks run C02 study > /tmp/c02-pallet-study.json
cmp /tmp/c02-pallet-study.json docs/C02_PALLET_STUDY_20261120.json
python -m unittest discover -s tests -p '*c02*.py' -v
```

The tests replay FIFO ownership, capacity, shifter exclusivity, transit time,
clearance and operation order. Fixtures cover both gapless station pairs,
simultaneous arrivals, blocked-transfer retries, warm-up and horizon events,
and deadlocks with and without staged pallets. `solve_c02_legacy` reproduces
the earlier delay abstraction. The spatial prototype remains under `experiments`.

## Sources

- J. Krauth, *Comparison 2 — Flexible Assembly System*, SNE 1(2), 1991, pp. 25–26. [Definition and clarifications](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_01/sne.01.2.pdf).
- T. Pingel and S. Pawletta, *A MATLAB-based Solution to ARGESIM Benchmark C2 using SimEvents*, 2011, listing 1, figures 2–3 and table 2. [Paper](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_21_34/articles/sne.21.34.10101.bn02.OA.pdf).
- F. Breitenecker and A. Kittenberger, *An Object-Oriented Solution of ARGESIM Comparison C2 with AnyLogic*, 2003, p. 22. [Paper](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_13/sne.13.37.pdf).
- S. Pllana and T. Fahringer, *An OO Programmed Approach to ARGESIM Comparison C2 with CSIM–C++*, 2003, p. 49. [Paper](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_13/sne.13.38-39.pdf).
- A. Herzog, *A Discrete Process Modelling Study of ARGESIM Benchmark C2 with Warteschlangensimulator*, 2024. The archived `SNE-C2.xml` contains the A2 and A3 decision scripts. [Paper](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_34_1/articles/sne.34.1.10673.bn02.OA.pdf) · [versioned model archive](https://github.com/A-Herzog/Warteschlangensimulator/blob/e61a05bf04c0e4bddd0c7a1876801b92becf1dd3/sne-benchmarks/SNE-C2.zip).
