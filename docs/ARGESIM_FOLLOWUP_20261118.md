# C04–C06 implementation review, 2026-11-18

This dated record documents the model choices and numerical probes introduced
in the November 18 follow-up to `c57c14ae`. The evidence file retains that
run's versions, counts, C02 counterexample and log hashes. For the present
catalog and the later C02 physical conveyor, see the current comparisons.
[Recorded checks](BENCHMARK_FOLLOWUP_20261118.json) ·
[Current comparisons](PUBLISHED_REFERENCE_CHECKS.md) · [C02 report](C02_IMPLEMENTATION.md)

## C04 refinement processes

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

A final event-order counterexample exposed another error in the unsafe policy:
an unrelated fork release could wake a philosopher before its scheduled second
acquisition. Waking a blocked philosopher now respects that pending delay.
The regression fixes the schedule: a release at 0.3 must not move acquisition
from 0.35 to 0.3, or meal completion from 0.45 to 0.4.

## C05 trajectories and measured precision

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

## C06 individual doctors and non-preemptive exchange

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

The later replicated C06 study compared 21 daily metrics under all three
service policies. [C06 numerical comparison](PUBLISHED_REFERENCE_CHECKS.md#c06-replicated-comparison)

The full contemporary account of the earlier C02 timing abstraction and CI
cleanup is available at its preserved revision. [Original review](https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks/blob/2c46b9dda31b32f215c0dc0824e9c0c40a9a67b4/docs/ARGESIM_FOLLOWUP_20261118.md)
