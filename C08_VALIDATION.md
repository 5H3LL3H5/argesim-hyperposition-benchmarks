# ARGESIM C08 Validation Evidence

The implementation covers the directional cycle policy, the one-barge lock,
anticipatory water-level changes, segregated and pooled transit-time measures,
and all Task-C variance-reduction activities.

Five committed deterministic tests reproduce the independent values in the
official appendix, including the 54-minute minimum transit time, the 54/88/122
within-cycle sequence, and Dataset 5's eastbound 94.67 and westbound 130-minute
means. Additional tests exercise ordinary and antithetic 90% intervals,
independent and common-random-number policy comparisons, interval-width changes,
and the prescribed null-hypothesis decision. This independent deterministic
oracle advances C08 to the `validated` gate; workload parity and retained timing
campaigns have not been established, so it is not `benchmark-ready`.
