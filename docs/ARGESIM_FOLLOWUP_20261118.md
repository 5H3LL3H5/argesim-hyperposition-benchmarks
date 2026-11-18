# Corrective implementation after the 24-family audit

This follow-up starts at `c57c14aea5fb8d8e5f099db5e898accb7d01bb4a` in PR #61.
It closes the identified implementation gaps in C04, C05 and C06, corrects
additional C02 timing errors, and addresses repository-wide Ruff findings.
The catalog now has 17 `implemented`, four limited `validated`, and three
incomplete (`specified`) families: C02, C18 and C20. No family is benchmark-ready.

## C04: actual refinement processes

The former `cleaning` policy acquired both forks atomically but did not clean
anything. Forks now become dirty after a meal and remain unavailable until a
scheduled cleaning completion. `completed_cleanings` exposes this process.
The default cleaning duration of 0.1 time units is an explicit modelling
choice; the original definition leaves timing distributions to the modeller.

The `requests` policy sends tokens to both neighbours after a configurable
waiting period (default 1.0). Requests are ordered by age, then philosopher ID;
a newer contender cannot take a requested fork ahead of its older requester.
Ongoing eating is not interrupted. Requests are removed when eating starts.

`c04_refinement_study` includes atomic acquisition, a deterministic circular-wait
deadlock, cleaning, neighbour requests, and two adversarial policies. `hoard`
retains both forks between meals; `targeted-hold` retains only forks shared
with designated victims. Initial thinking delays, conspirator IDs and victim
IDs are explicit inputs. Tests distinguish targeted starvation from depriving
both neighbours. Finite experiments do not prove universal starvation freedom.

Matched replication seeds are no longer described as guaranteed common random
numbers: different policy histories can consume random draws differently.

## C05: trajectories and measured precision

`simulate_c05` now returns sample times, states and active modes. It includes
every event and additional samples at 0.1, 1, 10 and 100 fast time constants
after the initial condition and switches. A coarse plotting grid alone would
hide these transients. A zero-duration exact step preserves the initial state.

`c05_task_c` executes the prescribed relative-accuracy settings of 1e-6, 1e-10
and 1e-14. Its backend uses the model's closed-form continuous flows, numerical
event bisection and decimal arithmetic with guard digits. It measures relative
errors in every event time and both final states against an 80-digit run;
the result includes requested precision, achieved errors and a pass flag.
It is not a newly implemented general-purpose stiff ODE solver, nor a proof
of the error bound at every point of a trajectory. C05 is an open comparison
of modelling/simulation approaches, so this semi-analytical implementation
is stated explicitly rather than presented as RK/QSS integration.

`c05_task_d` supplies the sampled 62-event trajectory and the prescribed
1e-11 precision experiment. Binary64 plotting output and the high-precision
accuracy report are separate fields. Decimal runs do not depend on, or mutate,
the caller's decimal precision and rounding context.

An independent 90-digit mpmath calculation uses logarithmic event equations,
not the candidate's bisection. The fast-mode term at these crossings is below
10**(-15000). It checks every event and both final states for both parameter
sets; the reproducible probe is `scripts/benchmark_spec_probe.py`.

For the transcribed decimal constants, the default final y1 is
`5.3693121235561020113543845033569230466...`; the last event occurs at
`4.9999996462203077505625813087999358748...` seconds. The previously cited
printed endpoint `5.3693121470` is approximately 2.34e-8 higher. It is useful
historical comparison data, but it cannot certify 1e-14 accuracy. The last
event's time error is amplified by the fast transient immediately before 5 s.

## C06: individual doctors and non-preemptive exchange

Four persistent doctor objects now retain their experience and actual busy
state. A patient is assigned to a free doctor; the service distribution follows
that doctor, not alternating service-start counters. An inexperienced doctor
working in CW1 receives the specified 20% duration penalty.

The definition does not specify interruption of ongoing treatment. This model
therefore exchanges a fixed pair after both finish their current patients.
An already idle partner waits for the other. The exchange is atomic, so each
ward retains two doctors, and no active treatment changes ward or doctor.
The >20 / <=5 waiting-queue hysteresis controls both exchange and return;
a pending exchange is cancelled if the queue recovers before it takes place.
This non-preemptive convention is explicit and is not an externally validated
unique interpretation of the underspecified handover timing.

Tests cover unequal service durations, stable identity, no mid-treatment move,
return exchange, cancellation of a pending exchange, returning-patient priority,
completion and seeded replay. The aggregate start-count alternation is removed.

## C02: correct dimensions expose a remaining reference mismatch

All shifters now take 2 s, including A1 and A6. B1/B2 lengths from the table
are not increased by the front-buffer length. The through path includes both
0.4 m shifter sections; initial placement uses the same lengths. B2 transport
is split before/after the positioning-unit centre, outside operation time.
An initially empty pallet receives only the 7.5 s loading operation at A1.

Unit tests check the complete isolated-station timeline. For A2 it is
2 + 1.6/0.3 + 60 + 2 = 69.333... seconds. The processing interval itself is
60 s. These timings were not fitted to the throughput reference.

Correcting the dimensions exposes a failure of the historical 6% throughput
comparison for ten pallets. The test retains its original numeric thresholds
and is marked `expectedFailure` with the missing model behaviour documented.
An unexpected success will require revisiting that marker; it is not counted
as a passing scientific check. The evidence JSON records all four comparison
cases, including failures. No benchmark validation gate is advanced.

Full belt occupancy, single-shifter contention, finite downstream buffers,
blocking propagation and Sy merge priority still need a physical transport
model. High-load cases remain explicitly unsupported, and deadlock remains
unknown for the partial abstraction. C02 stays `specified`.

## CI and remaining limitations

Ruff findings were fixed through import/export corrections, unused-variable
cleanup, bound loop closures, equivalent control-flow simplifications, accurate
context-manager annotations and executable modes for scripts with shebangs.
The Python-3.10 core remains dependency-free. Ruff's `typing-extensions` fallback
is disabled to prevent a lint autofix introducing an undeclared runtime import.
Two broad exception handlers are deliberately retained and annotated: suite
execution and isolated performance measurement must record arbitrary task
failures and continue. No global lint rule is disabled.

C18 still lacks the original 100 Hz measurements. Rechecking the active ARGESIM
and SNE C18 pages found descriptions of a download but no measurement-file link;
the figure digitizations remain explicitly labelled substitutes. C20 still
lacks demonstrated equivalence of its reduced conveyor network to the physical
layout and its blocking rules. Neither is promoted by this follow-up.

Publication-scale stochastic validation, mesh convergence, all solver variants
and parallel-performance qualification remain separate work. Verification
commands, source hashes and actual results are recorded in the follow-up
evidence JSON; successful smoke execution is not scientific certification.

## Verification of the follow-up

Local checks used CPython 3.12.14. Exact commands, source hashes, log digests,
individual numerical checks and C02 comparison results are retained in
[BENCHMARK_FOLLOWUP_20261118.json](BENCHMARK_FOLLOWUP_20261118.json).

| Check | Observed result |
|---|---|
| Complete unit suite | 341 tests: 340 passed, one expected C02 reference failure |
| Final C02/C04/C05/C06 regression rerun | 32 tests: 31 passed, the same expected failure |
| Complete smoke profile | 74/74 tasks passed across all 24 families |
| Final C04/C05 smoke rerun | 7/7 tasks passed |
| Independent numerical probes | 11/11 passed, including both C05 precision references |
| Ruff 0.17.5 | Zero findings |
| Compile, generated-status and diff checks | Passed |
| Core import and C05 precision with `python -S` | Passed without site packages |

The full unit run preceded the last C04 deadlock-detection refinement and an
additional C02 execution assertion; the 32-test rerun covers those final files.
The full smoke run preceded the C05 decimal-context isolation and final C04
refinement; their seven tasks were rerun afterwards. These are overlapping
checks, not additional independent test totals.

The ten-pallet C02 case yields throughput 1209 versus reference 959 (+26.07%)
and mean transit 238.69 s versus 285 s (-16.25%). The 14-, 20- and 40-pallet
cases remain within the historical 6% bounds. This does not establish the
missing blocking/deadlock behaviour. The expected-failure marker preserves
the original tolerance and keeps this unresolved result visible.

The GitHub matrix for the preceding audit commit passed unit tests on Python
3.10–3.13 but failed its Python-3.13 Ruff step. This follow-up pins Ruff 0.17.5
and fixes the reported findings. Hosted results for this new commit must be
read from PR #61; preceding CI results do not certify the follow-up.
