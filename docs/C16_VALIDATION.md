# C16 restaurant validation

C16 reaches `validated` for the **mean number of restaurants at the end of year five** in Task A. The reference checker compares the count at week 260 for 50 independent replications with two published 50-run studies. The single example trajectory and the time average after year five are separate outputs. [Recorded inputs and counts](C16_REFERENCE_RESULTS.json) · [AnyLogic and Java sources](PUBLISHED_REFERENCE_CHECKS.md#c16-restaurant-count-and-economic-studies)

| Week-260 count | Mean | Sample variance |
|---|---:|---:|
| Registered model, seed 42 | 5.72 | 1.104 |
| Published AnyLogic | 6.34 | 1.98 |
| Published Java OO | 6.06 | 2.02 |

The acceptance band is three estimated standard errors of the difference of the means plus 0.005 for rounding. The differences of 0.62 and 0.34 restaurants fall inside the respective bands of 0.750 and 0.755. The local counts vary less than either published sample. The mean over weeks 261–520 is 6.04946. [Comparison script](../scripts/c16_reference_check.py)

## Reproduce the week-260 comparison

The full run uses the default population, 50 replications and a separate ten-year example trajectory. Workers process the same ordered seeds as the serial version.

```sh
python -m argesim_benchmarks run C16 A --kwargs-json '{"workers":6}' | python scripts/c16_reference_check.py
```

Task B reports mean cumulative tax across five runs per rate. Task C pools the lifetime revenues observed for restaurants that opened during each run. The tax and revenue studies have different observation windows from the published comparisons. Their outcomes are reported alongside the Task A evidence. [Economic study](PUBLISHED_REFERENCE_CHECKS.md#c16-restaurant-count-and-economic-studies) · [Event semantics](C16_DEVS_SPECIFICATION.md)
