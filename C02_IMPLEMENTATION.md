# C02 flexible assembly system

The registered solver runs the eight-station plant and the pallet-count study
with finite conveyor storage. C02 reaches the repository's `implemented`
gate. The 10-, 14-, 20- and 40-pallet regression cases pass the existing 6%
band for both throughput and mean part time. The 25-pallet mean and the
choice of optimum remain open reference comparisons.

## Transport and controller

A B1 segment holds five complete 0.36 m pallets at A1/A6 and four at each
other station. B2 has an input buffer (three or two pallets respectively),
one 0.4 m positioning unit and a one-pallet output buffer. Six 0.4 m
connectors each hold one pallet. All lengths, shifts and operation times
come from Krauth's Table 1 and clarifications. The model advances to the
next event on a lattice of 1/30 s at the nominal 18 m/min belt speed.
FIFO entries and exits are separated by at least one pallet pitch.
Travel to the centre of a positioning unit, processing, and travel out
are three distinct intervals. An occupied output buffer can block the unit.

Passing straight across a shifter takes 0.4 m / 0.3 m/s. A lateral transfer
occupies it for 2 s, following the two alternatives in clarification 1.
A pallet reserves a destination before entering either shifter. At A2_3→A3
and A6→A1 it books the contiguous Sy and Sx crossing intervals plus the
final B1 or B2 space in one decision. A blocked transfer stays upstream.
At Sy, an admissible B2 return takes precedence over an admissible B1
arrival at the same tick.

One controller is used for all populations. A pallet takes the first eligible
A2 with input space, before or after the complete A3/A4/A5 group. This is the
A2 rule in Pingel and Pawletta's listing. For the group, A3 takes eligible
work when A6's unit is busy, and A4/A5 require their preceding operation(s).
A6 performs all remaining group operations in one 30 s service. This choice
of A6 policy follows Breitenecker and Kittenberger. The SimEvents paper
publishes its A2 logic but does not specify every A3–A6 decision or initial
pallet position. The comparisons below consequently apply to this
documented controller and startup.

## Startup and clocks

Empty pallets start spread deterministically over the 40 legal resting
places on B1 and its connectors. The selection uses evenly spaced indices
in the ordered list of places. Larger populations start with 40 on B1 and
admit the surplus empty pallets through A1's B1 entrance as it clears.
The source yields to circulating traffic. Pllana and Fahringer describe
the difficulty of putting 60 empty pallets on B1 at time zero. Reporting
the initial population, time of final admission and any pending pallets
makes this startup convention reproducible. Every run in the study was
fully admitted by 526 s, before measurement.

The observation window includes completed unloadings from 7,200 through
36,000 s. The timestamp of a workpiece loaded before the window carries
over. Throughput counts parts when unloading finishes. For that same set
of parts the solver returns three independently timed intervals.

| Field | Start at A1 | End at A1 |
|---|---|---|
| `average_throughput_time` (s) | Loading complete | Unloading starts |
| `average_to_unload_complete_seconds` | Loading complete | Unloading complete |
| `average_including_handling_seconds` | Loading starts | Unloading complete |

This makes the change from the legacy solver's consecutive A1 discharge
timestamps explicit. For example, with 14 pallets the intervals are
280.22, 287.72 and 295.22 s. The first interval is used throughout the
SimEvents comparison. Its paper gives aggregate timer results without a
full event log for locating each 7.5 s handling interval. With no observed
completions, throughput is zero and all three means are null.

## Comparison with SimEvents Table 2

The table includes every numerical row of the published study. Eleven of
the twelve rows meet the 6% band for both measures. All twelve throughput
counts meet it.

| Pallets | Published count | Model count | Published mean (s) | Model mean (s) | Mean difference |
|---:|---:|---:|---:|---:|---:|
| 10 | 959 | 939 | 285 | 291.71 | +2.36% |
| 11 | 1072 | 1056 | 280 | 284.81 | +1.72% |
| 12 | 1185 | 1174 | 276 | 279.38 | +1.22% |
| 13 | 1298 | 1263 | 273 | 281.21 | +3.01% |
| 14 | 1439 | 1365 | 265 | 280.22 | +5.74% |
| 15 | 1439 | 1409 | 285 | 291.64 | +2.33% |
| 20 | 1439 | 1410 | 385 | 393.68 | +2.25% |
| 25 | 1439 | 1409 | 396 | 496.73 | +25.44% |
| 30 | 1440 | 1410 | 586 | 597.84 | +2.02% |
| 35 | 1438 | 1408 | 682 | 700.54 | +2.72% |
| 40 | 1437 | 1409 | 787 | 800.54 | +1.72% |
| 45 | 1440 | 1407 | 882 | 901.85 | +2.25% |

For all 49 populations from 1 to 49, production continues to the observation
horizon. Every population from 50 to 60 reaches a physical gridlock after
all pallets enter the plant. At 50 the gridlock is recorded at 2,206.60 s,
and at 60 at 1,199.27 s. The individual run returns the terminal inventory
and a wait-for graph. Every blocked resource waits exclusively on other
full, blocked resources. The plant also checks for outstanding service,
belt motion and reserved crossings before declaring deadlock.

The study ranks fully admitted, productive runs by measured eight-hour
throughput, then by shortest mean part time, then by fewest pallets. Its
maximum is 1,411 parts with 22 pallets (434.35 s mean). Already at 15 pallets
the plant produces 1,409 parts (291.64 s). The three A2 units each require
60 s of processing plus 0.4/0.3 s of positioning travel. Their nominal
steady rate corresponds to 1,408.70 parts per eight hours. Work already in
process at the window boundaries affects the integer count. The SimEvents
authors report an optimum of 14. The full controller, startup and measurement
traces would be needed to resolve the difference.

## Reproduction

The full sweep is [archived as CLI output](docs/C02_PALLET_STUDY_20261120.json).

```sh
python -m argesim_benchmarks run C02 main --kwargs-json '{"num_pallets": 60}'
python -m argesim_benchmarks run C02 study > /tmp/c02-pallet-study.json
cmp /tmp/c02-pallet-study.json docs/C02_PALLET_STUDY_20261120.json
python -m unittest discover -s tests -p '*c02*.py' -v
```

The tests independently replay transfers for FIFO ownership, capacities,
shifter exclusivity, transit times and pitch. Other fixtures cover blocked
and simultaneous transfers, both gapless pairs, warm-up and horizon events,
and high-load deadlock witnesses. For a single pallet the uncongested route
visits A1/A2/A6. Translating 13.6 m of subsystem belts and 2.4 m of
connectors, passing ten shifters straight, and shifting laterally six times
takes 78.6667 s. Adding 60 s at A2 and 30 s at A6 gives the model's
168.6667 s mean part time without A1 handling.

For historical reproduction, `solve_c02_legacy` runs the earlier delay
abstraction. The earlier spatial prototype remains under `experiments`.

## Sources

- J. Krauth, *Comparison 2: Flexible Assembly System*, definition and clarifications, SNE 1(2), 1991, pp. 25–26. [Original issue](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_01/sne.01.2.pdf).
- T. Pingel and S. Pawletta, *A MATLAB-based Solution to ARGESIM Benchmark C2 using SimEvents*, 2011, listing 1, figures 2–3 and table 2. [Paper](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_21_34/articles/sne.21.34.10101.bn02.OA.pdf).
- F. Breitenecker and A. Kittenberger, *An Object-Oriented Solution of ARGESIM Comparison C2 with AnyLogic*, SNE 13(37), 2003, p. 22. [Controller and station-capacity calculation](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_13/sne.13.37.pdf).
- S. Pllana and T. Fahringer, *An OO Programmed Approach to ARGESIM Comparison C2 with CSIM–C++*, SNE 13(38/39), 2003, p. 49. [Initial storage and finite-window counting](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_13/sne.13.38-39.pdf).
