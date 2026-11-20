# ARGESIM numerical reference checks

The catalog has 24 families. Thirteen reach `validated` for the cases identified below. Ten reach `implemented`. C18 remains at `specified`. A smoke run checks executability. The scientific comparisons use separate published numbers, analytical solutions or independently integrated equations.

## Cases with numerical references

| Family | Evidence and scope |
|---|---|
| C01 | Across all five Task B loss rates, every stored RK45 sample agrees with independent Radau integration within `1.51e-8`. Each component at 10 s meets the `2e-7` regression tolerance. The two Task C stationary states agree with Dymola. [Trajectories, endpoints and source](C01_RESULTS.md) |
| C03 | Four ON/OFF eigenvalues per switch state, 20 ideal-switch half cycles and four finite-ramp endpoints computed independently with Radau and matrix exponentials. [Circuit and tolerances](../C03_VALIDATION_REPORT.md) |
| C05 | Five default events, 62 Task D switches, return states and the published initial/final event times. An independent 90-digit calculation checks the decimal precision study. [Ptolemy II, p. 54](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_22_1/articles/sne.22.1.10117.bn05.OA.pdf) |
| C06 | All 21 daily metrics for the FIFO, doctor-exchange and return-priority policies meet the statistical comparison below. [STROBOSCOPE, Table 1](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_36_1/articles/sne.36.1.10769.bn06.OA.pdf) |
| C07 | Eight Task A(i) nonlinear pin crossings match published MATLAB column F within 1 ms. An independent event-driven DOP853 calculation covers both Task A initial conditions. [Setinek et al., Table 3](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_31_4/articles/sne.31.4.10589.bne.OA.pdf) |
| C08 | Five deterministic appendix datasets cover the canal/lock policies. Stochastic replication and interval tests are also present. [Case evidence](../C08_VALIDATION.md) |
| C12 | The inverse solution gives restitution 0.58740105. For 10,000 samples, the fourth sphere's mean terminal speed is 0.42322 and its standard deviation is 0.04294. Both fall in the intervals published for the Dymola experiment. [Dymola, Task C](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C12/C12-solution-Dymola.pdf) |
| C15 | All three Task A numerical bolus masses agree within 0.01 with the Maxima/LISP publication at 1.5, 4 and 240 min. The Task B fit yields a squared residual of 260.80663. The published MATLAB value is 260.8067. Task C runs 1,000 perturbed fits. Different studies report different parameter dispersions. [Maxima/LISP](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C15/C15-solution-Maxima.pdf) · [MATLAB](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C15/C15-solution-MATLAB.pdf) |
| C16 | The mean restaurant count at the end of year five meets the declared comparison criterion for two independent 50-replication studies. The simulated counts have lower variance. The economic studies use different observation windows. [C16 results](#c16-restaurant-count-and-economic-studies) |
| C21 | Published ball-contact and pendulum stop/kick cases, plus the RLC algebraic residual. [Coverage](../ARGESIM_COVERAGE.md) |
| C22 | The ten published jockeying records, all four abandonments and the ten deterministic class waiting-time statistics match MatlabGPSS to printed precision. Only customers already waiting at a call can join that service group. Later arrivals wait for another call. STROBOSCOPE reports different class statistics under its queue-filter implementation. [MatlabGPSS, Tables 3, 5, 7](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_29_4/articles/sne.29.4.10496.bn22.OA.pdf) · [STROBOSCOPE, Table 8](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_35_4/articles/sne.35.4.10751.bn22.OA.pdf) |
| CP1 | Published ten-population endpoint for Task B. Serial/parallel comparisons cover additional workloads. [Coverage](../ARGESIM_COVERAGE.md) |
| CP2 | Corrected rope/Fourier reference and LBM algorithm checks. Full publication-sized cavity timings are outside this comparison. [Coverage](../ARGESIM_COVERAGE.md) |

## C06 replicated comparison

Each policy runs 100 independent days of 250 patients, with seeds 0–99. The columns below give means over days. Closing is measured from 07:30 to the last departure. Daily patient dispersion is calculated within each day. For each printed whole-minute target, the regression uses half a minute for rounding plus 3.5 estimated standard errors of the difference between two 100-day means, assuming comparable between-day variance. STROBOSCOPE reports rounded means without per-replication variances.

| Measure (minutes) | A model / paper | B model / paper | C model / paper |
|---|---:|---:|---:|
| All patients | 174.17 / 174 | 185.26 / 184 | 161.68 / 161 |
| Type 1 | 236.91 / 237 | 251.86 / 252 | 163.11 / 164 |
| Type 2 | 137.63 / 136 | 145.19 / 144 | 164.22 / 162 |
| Type 3 | 248.47 / 252 | 259.80 / 266 | 170.91 / 175 |
| Type 4 | 127.80 / 127 | 137.25 / 136 | 157.72 / 156 |
| Daily standard deviation | 80.96 / 82 | 93.53 / 95 | 74.73 / 75 |
| Last departure | 376.00 / 378 | 419.33 / 420 | 379.51 / 382 |

## Remaining families

| Family | Verified or corrected | Remaining numerical evidence |
|---|---|---|
| C02 | One service-only configuration meets the existing 6% band for both metrics at all 11 CSIM loads. At 25 pallets the full-clock means are 500.68 s here and 499.33 s in CSIM. | The default fails the SimEvents comparisons at 13, 14 and 25 pallets. A fixed seeded variant matches 11 of 12. Its part clock still differs from the published 396 s at 25 pallets. The original SimEvents model and evaluation function were unavailable. [Both tables and clock definitions](../C02_IMPLEMENTATION.md) |
| C04 | Fork ownership, cleaning, starvation/deadlock cases and seeded per-philosopher accounting. | A matched policy and timing distribution are needed to compare fairness statistics across implementations. |
| C09 | Published control surfaces, units, disturbance direction and long closed-loop runs. | Output traces with a matched sampled-controller convention are needed for numerical trajectory validation. |
| C10 | Simultaneous access priority, deadlock termination and the 50-run experiment. | Published stochastic waiting/deadlock distributions have not been matched with the same event and randomization conventions. |
| C11 | Robot dynamics, control tasks and numerical residual checks. | Published controller trajectories under matching gains, sampling and initial conditions are outstanding. |
| C13 | Independent plant checks distinguish the 2006 and revised 2007 damping parameters. | Published Task B/C traces for the revised parameters remain outstanding. |
| C14 | Midnight demand belongs to the new day. The reported sale-triggered Task A ordering rule is selectable alongside literal daily ordering. All three policies have 100-run comparisons. | Reference implementations disagree on Task A ordering and costs. The default and published variants are identified separately. [Results and sources](../C14_VALIDATION.md) |
| C17R | Aggregate conservation and seeded numerical replay. | Independent matched numeric trajectories remain outstanding. |
| C18 | Published linear model on the digitized training/validation curves gives 0.95347/0.94231. The recurrent model gives 0.99377/0.92642 on separate muscles. | Neither original recording was located in the publisher archives. The recovered figures support a separate reconstruction experiment. [Data provenance and searches](C18_FIGURE_RECONSTRUCTION.md) |
| C19R | Table 1 parameters, finite-volume source and sink areas, weekday switching and numerical homogeneous profiles. | The 1 m grid retains measurable spatial error at breakthrough and near the treatment disks. See the numerical comparisons below. |
| C20 | The archived 360 runs complete 1,800,000 orders. All five model/replay file hashes match the archived experiment. Its checkpoint wrapper subsequently changed. | The original three FlexSim order books and matching reservation controller are required for external production-output parity. [Full protocol and replay](ARGESIM_CLOSURE_20261120.md) |

## C16 restaurant count and economic studies

The definition requests 50 independent replications for Task A. AnyLogic and
Java report the number of restaurants at the end of the fifth year. The
registered task returns all 50 counts at week 260 and their mean. It also
returns the previously reported time average over weeks 261–520. The
exemplar trajectory has a separate seed. Serial and parallel execution use
the same ordered replication seeds. [Definition](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C16/C16-definition.pdf) · [AnyLogic](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C16/C16-solution-AnyLogic.pdf) · [Java](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C16/C16-solution-Java-OO.pdf)

The former one-million-event budget stopped Task B before the end of year five
and Task C before the end of year ten. A diner visits at most once per day and
the financial accounts close once every seven days. C16 uses these bounds to
size its default event budget for the requested horizon. The explicit
`max_events` argument still enforces a caller's limit.

For the endpoint comparison, use the reported 50-run variance for each
publication and the sample variance from the candidate. Accept a difference
of up to three estimated standard errors of the difference of means plus
0.005 for rounding. Each side has 50 replications. The reference checker
reports both comparisons and the candidate counts.

| At week 260, 50 replications | Mean | Variance | Minimum | Maximum |
|---|---:|---:|---:|---:|
| Registered model, seed 42 | 5.72 | 1.104 | 4 | 8 |
| AnyLogic | 6.34 | 1.98 | 4 | 10 |
| Java OO | 6.06 | 2.02 | 4 | 9 |

The mean is 2.50 estimated standard errors below AnyLogic and 1.36 below
Java. The catalog classification covers the week-260 mean. The sample is
less dispersed than either published sample. The mean over weeks 261–520 is
6.04946. [Counts, inputs and economic results](C16_REFERENCE_RESULTS.json)

```bash
python -m argesim_benchmarks run C16 A --kwargs-json '{"workers": 6}' | python scripts/c16_reference_check.py
```

Task B runs five replications at each of the 21 tax rates from 0% to 100%.
Across five simulated years, the largest mean tax income is 224,840.24 at
40%. The Java study found 37.8% over two years on a finer tax grid. AnyLogic
reported 39.85% for its observation window from day 180 to year two. These
windows permit comparison of the maximizing rate only. [Java](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C16/C16-solution-Java-OO.pdf) · [AnyLogic](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C16/C16-solution-AnyLogic.pdf)

Task C covers all 13 density exponents from 0 to 6. Each value uses five
ten-year runs. The largest pooled mean lifetime revenue of new restaurants
is 10,569.96 at `k=0.5`. AnyLogic also selected 0.5 using a five-year revenue
measure. Java selected 1.0 using weekly revenue. Differences in the revenue
definition and horizon limit the monetary comparison. [AnyLogic](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C16/C16-solution-AnyLogic.pdf) · [Java](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C16/C16-solution-Java-OO.pdf)

## C19R spatial and time accuracy


Table 1 of the revised definition gives a pore velocity of `1e-5 m/s`, equivalent to 0.864 m/day. The adjacent prose says about 1.7 m/day. The COMSOL model's settings show `10^(-5)`. The registered model follows Table 1. Its conservative advection flux uses a monotonized central limiter. Treatment rates use the actual disk area in each cell. A subgrid receives source mass only when it contains the origin. Scheduled integration ends a step at every change of treatment mode. [Definition, p. 64](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_16_34/sne.16.34.pdf) · [COMSOL, Fig. 5](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C19/C19R-solution-COMSOL.pdf)

The Task A profile option also integrates the homogeneous point-source response over time using numerical quadrature. The comparison script independently integrates the heat kernel using a Gaussian change of variable and SciPy. Both agree at all 123 prescribed profile points. The definition prints an erfc approximation with its own early-time error.

| At (50 m, 0 m), mg/m³ | Day 50 | Day 100 | Day 150 |
|---|---:|---:|---:|
| Homogeneous infinite-plane numerical integral | 7.60657 | 14,269.43 | 14,269.43 |
| Printed analytical approximation | 0.02650 | 14,272.99 | 14,272.99 |
| 1 m finite-volume grid, A | 0.00152 | 14,613.39 | 14,613.39 |

COMSOL Figure 2 shows a day-50 peak near 7.6. Figure 6 shows roughly 5,200 mg/m³ for continuous treatment and a weekly oscillation around 7,300 mg/m³. The 1 m grid gives 5,564 mg/m³ for continuous treatment at day 100. The scheduled calculation spans 7,578–7,938 mg/m³ over the preceding week. Values read from the figures are approximate. [COMSOL study, p. 80](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C19/C19R-solution-COMSOL.pdf)

```sh
python -m argesim_benchmarks run C19R A --kwargs-json '{"profiles":true}'
python scripts/c19_profiles.py > c19-profiles.json
python -m unittest discover -s tests -v
python -m argesim_benchmarks run-suite --profile smoke
```

The script exports Task A profiles at days 50, 100 and 150, all three Task B profiles at day 100, and hourly continuous/scheduled concentrations at (50, 0) through day 150.
