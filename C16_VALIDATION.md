# ARGESIM C16 Implementation Evidence

## Implemented definition

The model transcribes the official C16 population, city, restaurant, financial,
and stochastic rules. In particular:

- the 30 initial restaurants use the required 6 x 5 centred grid with horizontal
  spacing 100 and vertical spacing 80;
- a week-boundary dinner is processed before financial accounting;
- restaurant density is `sum((1 / distance) ** k)`, including the defined `k=0`
  limit;
- Task B averages government tax income over replicated simulations using common
  run seeds across tax rates; and
- Task C measures lifetime revenue of restaurants opened during the simulation,
  rather than total system revenue.

## Committed checks

The tests verify the official grid coordinates, the density exponent, confluent
week-boundary order, exclusion of initial restaurants from Task C revenue, task
output shapes, and invalid-input handling. The benchmark runner can generate the
1-, 5-, and 10-year count trajectories and replicated Task B/C parameter studies.

## Evidence boundary

Published solutions use different random-number streams and sometimes document
model simplifications. Their aggregate outcomes are useful context but are not an
independent deterministic oracle. No workload-parity study or retained raw timing
campaign is present. C16 therefore remains at the `implemented` gate, not
`validated` or `benchmark-ready`.
