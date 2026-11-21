# C16 dining and weekly accounting in superdense time

The registered restaurant model is a closed stochastic discrete-event system. One `C16Simulation` owns the people, the current restaurant list, a seeded random generator and a `DesScheduler`. Each person has a pending dining event. A single weekly callback updates all restaurants and replaces their membership together. [Model and parameters](../argesim_benchmarks/models/c16_restaurant_business.py)

## State and time advance

By default, 3,000 people occupy five city regions in a 600 × 400 area. Their positions stay fixed. The initial 30 restaurants form a centred six-column, five-row grid with spacings 100 and 80. Each restaurant carries an ID, its initial/opened-in-run flag, weekly revenue and lifetime revenue. The simulation also tracks total tax and the lifetime revenue of new restaurants that have closed.

| Event | Scheduled time (day, microstep) | Transition |
|---|---|---|
| Dinner for person $p$ | $(d,0)$, with each interval drawn uniformly from the integers 1–8 | Choose uniformly among open restaurants within distance 100. If a restaurant is available, credit the dinner cost to both revenue totals. Schedule the next visit even if none is in range. |
| Weekly accounts | $(7k,1)$ for $k=1,2,\ldots$ | Evaluate weekly tax and profit for each existing restaurant, collect closures and openings, replace the restaurant list and schedule the next weekly close. |

At a week boundary every dinner at microstep 0 precedes the accounts at microstep 1. A dinner on day seven contributes to that week's profit. All opening locations in that callback are evaluated against the restaurant list at the start of accounting. Newly opened restaurants become available for visits after the callback. The finite run horizon includes both microsteps. [Scheduler](../nsa_devs/scheduler.py) · [Boundary-order tests](../tests/test_c16.py)

## Financial and location rules

For weekly revenue $R$, running cost $C$ and tax rate $t$, tax is $t\max(R-C,0)$ and profit is $R-C-\mathrm{tax}$. Defaults are a dinner cost of 1, running cost of 150, tax rate of 20% and profit threshold of 350. A restaurant strictly above the threshold opens a new restaurant with probability 0.10. One strictly below closes with probability 0.20. At equality the restaurant stays open. Weekly revenue resets after assessment.

The default area is divided into 30 columns and 20 rows, with cells 20 units on each side. Its score at the cell centre is the number of residents in that cell divided by $\sum_r (1/d_r)^k$, where $d_r$ is the distance to each existing restaurant and $k=4$ by default. At $k=0$ every restaurant contributes one. The simulation draws among tied best cells, then draws a location inside the chosen cell.

## Observables

Task A records weekly counts for an example trajectory and week-260 counts across the replicated runs. Task B collects tax. Task C includes both closed and surviving restaurants opened during the run when computing revenue. The independent reference comparison applies to the Task A week-260 mean. [Validation report](C16_VALIDATION.md)
