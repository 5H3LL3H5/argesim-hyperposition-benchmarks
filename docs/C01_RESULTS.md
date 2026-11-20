# C01 numerical validation and implementation checks

C01 meets the catalog's `validated` gate for the default Task A trajectory,
the five Task B loss rates and the two Task C stationary states. The transient
reference uses independently transcribed equations and SciPy Radau. The
stationary reference comes from the published Dymola solution. The Task A
timing experiment also has a separate within-solver accuracy check.

## Experiment Setup

* **Model**: ARGESIM C01 Lithium-Cluster Dynamics (Stiff ODE)
* **Initial State**: $r(0) = 84.99$, $m(0) = 1.674$, $f(0) = 9.975$
* **Initial Parameters**: $k_r = 1.0$, $k_f = 0.1$, $loss_f = 1000.0$, $decay_r = 0.1$, $decay_m = 1.0$
* **Runs**: For Task A timing, 9 timed repetitions and 1 warmup run were executed per solver method (Euler, RK4, RK45, QSS1) using `benchmark_argesim_c01.py`.

## Verification Evidence

### Task A (Simulation of the Stiff System)
For the timing experiment, the repository's RK45 with `rtol=1.0e-11`,
`atol=1.0e-14` and `max_step=2.0e-3` gives the endpoint
`(31.75561249, 3.47967131, 0.01010072)`

Each timed method meets its own endpoint tolerance. The default RK45 differs
from the tight RK45 endpoint by about `1.08e-10`. The independent comparison
for the same default trajectory appears in the 1,000 loss-rate row below.

### Task B (Parameter Variation)
The independent probe integrates the three equations with SciPy Radau over
0–10 s using `rtol=2e-12` and `atol=2e-13`. Its dense output is evaluated
at every stored RK45 time. The maximum absolute error is taken over all three
components and all samples for each loss rate. The tolerance is `2e-6`.
The regression suite also checks each component at 10 s against the archived
Radau endpoint with absolute tolerance `2e-7`.

| Loss rate | RK45 samples | Radau endpoint (r, m, f) | Maximum trajectory error |
|---:|---:|---|---:|
| 100 | 1,072 | (35.506204997109, 3.479215004071, 0.101616870993) | 1.506e-8 |
| $10^{2.5}$ | 1,140 | (32.756541018625, 3.487300514722, 0.032069274358) | 1.484e-8 |
| 1,000 | 3,164 | (31.755612494065, 3.479671316355, 0.010100722053) | 1.461e-8 |
| $10^{3.5}$ | 9,688 | (31.422834488577, 3.475750569249, 0.003188529708) | 1.466e-8 |
| 10,000 | 30,363 | (31.315845979889, 3.474338071668, 0.001007685996) | 1.470e-8 |

Run `python scripts/benchmark_spec_probe.py` to reproduce the trajectory
comparisons and reference endpoints. The recorded run used SciPy 1.17.0 and
NumPy 2.3.5. [Independent equations](../scripts/benchmark_spec_probe.py) ·
[Endpoint regressions](../tests/test_argesim_c01.py)

### Task C (Steady State Verification)
The analytical stationary states agree with Dymola Task C. Constant
bombardment at $p=10000$ gives $(r,m,f)=(1000,10,10)$. At $p=0$ all three
populations are zero. The test also substitutes the nonzero stationary state
back into the ODE and checks that each derivative has magnitude below
`1e-12`. [Published Dymola solution](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C01/C1-solution-Dymola.pdf)

---

## Detailed Task A Timing Data

The runtime data compare the declared solver workloads only after each result has
passed its implementation-level endpoint tolerance.  They do not establish
benchmark-ready workload parity across tools.

```json
{
  "benchmark": "ARGESIM-C01-task-A",
  "definition": "https://www.argesim.org/benchmarks/c01/",
  "reference_endpoint": [
    31.755612494065243,
    3.4796713163550073,
    0.010100722052653936
  ],
  "methods": {
    "euler": {
      "endpoint": [
        31.75486748095361,
        3.479591762205645,
        0.01010049003473013
      ],
      "maximum_endpoint_error": 0.0007450131116328862,
      "error_tolerance": 0.0008,
      "accepted_steps_or_events": 20000,
      "rejected_steps": 0,
      "rhs_evaluations": 20000,
      "durations_ns": [
        179178286,
        185014934,
        186217936,
        182036903,
        180049235,
        181290032,
        181051116,
        181837329,
        181495097
      ],
      "median_ns": 181495097,
      "iqr_ns": 985787.0
    },
    "rk4": {
      "endpoint": [
        31.755615454270348,
        3.4796716436033854,
        0.010100722996689416
      ],
      "maximum_endpoint_error": 2.960205105040359e-06,
      "error_tolerance": 4e-06,
      "accepted_steps_or_events": 10001,
      "rejected_steps": 0,
      "rhs_evaluations": 40004,
      "durations_ns": [
        325861418,
        329378330,
        330584044,
        326129213,
        329238253,
        328147414,
        327245181,
        325534062,
        326655714
      ],
      "median_ns": 327245181,
      "iqr_ns": 3109040.0
    },
    "rk45": {
      "endpoint": [
        31.7556124940653,
        3.4796713163546,
        0.010100721943916506
      ],
      "maximum_endpoint_error": 1.0873743051809104e-10,
      "error_tolerance": 2e-09,
      "accepted_steps_or_events": 3163,
      "rejected_steps": 58,
      "rhs_evaluations": 22547,
      "durations_ns": [
        216713904,
        216267186,
        216144824,
        215051706,
        216392616,
        214974439,
        215257855,
        214632041,
        215200768
      ],
      "median_ns": 215257855,
      "iqr_ns": 1215480.0
    },
    "qss1": {
      "endpoint": [
        31.75251710445245,
        3.4793780338041422,
        0.010156335244218979
      ],
      "maximum_endpoint_error": 0.0030953896127918767,
      "error_tolerance": 0.004,
      "accepted_steps_or_events": 116125,
      "rejected_steps": 0,
      "rhs_evaluations": 116126,
      "durations_ns": [
        1024312088,
        1266568364,
        1037297384,
        1040887469,
        1034851187,
        1043938393,
        1038067031,
        2063546922,
        1345176673
      ],
      "median_ns": 1040887469,
      "iqr_ns": 229270980.0
    }
  },
  "interpretation": "Runtime comparisons are reported only after every endpoint passes its declared accuracy threshold. Solver configuration and work counts differ and are therefore retained with the timing data."
}

```
