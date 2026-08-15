# ARGESIM Benchmark C10 Implementation Evidence

## Experiment
The ARGESIM C10 "Dining Philosophers II" benchmark involves 5 philosophers sitting around a table with 5 chopsticks. Philosophers alternate between Thinking, Waiting, and Eating. According to the strict definition for simultaneous access: if philosopher $i$ requests their right chopstick at the same time philosopher $i+1$ requests their left chopstick (the same object), philosopher $i+1$ gets it first. Deadlock occurs when all 5 philosophers are waiting for their right chopstick.

## Runs and Parameters
- **Time Distribution:** Discrete uniform [1, 10] for both Thinking and Eating.
- **Initial State:** All 5 philosophers start in the Thinking state.
- **Task A Runs:** A single run until deadlock occurs, extracting mean and standard deviations for state durations, and chopstick utilizations.
- **Task B Runs:** 50 independent runs, each until deadlock, computing maximum and minimum termination times.

## Outcome and evidence boundary
The model was implemented natively as a custom Discrete Event Simulator priority queue in `argesim_benchmarks/models/c10_dining_philosophers.py`.

The following table compares our implementation against existing literature. The "Strict C10 Definition" (e.g., Löscher/Breitenecker 2005) follows the deadlock-prone ruleset, whereas the "EZStrobe Solution" (Ioannou et al. 2026) deliberately alters chopstick acquisition to avoid deadlock.

| Implementation | Average Waiting Time | Chopstick Utilization | Deadlock Capable |
| :--- | :--- | :--- | :--- |
| **Our Model Output** (`seed=42`) | ~12.7 time units | ~92% | Yes |
| **Strict C10 Literature** ([3], [4]) | ~11.5 time units | 92% | Yes |
| **EZStrobe Non-Deadlocking** (2026) | 4.19 time units | 72% | No |

- **Evidence level:** implemented. The model executes both required tasks and
  archives production-generated simultaneous-access traces.  The cited summary
  statistics are contextual comparisons, not an independent validation oracle,
  so this evidence does not advance C10 to the `validated` gate.

## Methodology Note
The committed tests exercise the same resolver used by the simulation and verify
the required right-neighbour priority rule.  No uncommitted plot or manually
inspected artifact is treated as validation evidence.
