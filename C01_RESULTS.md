# C01 Benchmark Results

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
