# C01 numerical validation and implementation checks

C01 meets the catalog's `validated` gate for the default Task A trajectory,
the five Task B loss rates and the two Task C stationary states. The transient
reference uses independently transcribed equations and SciPy Radau. The
stationary reference comes from the published Dymola solution. The Task A
timing experiment also has a separate within-solver accuracy check.

## Task A trajectory and timing check

The state starts at `(r, m, f) = (84.99, 1.674, 9.975)`. Bombardment is
switched off and the default loss rate is 1,000. The independent check for
this trajectory is the middle row of the Task B table.

The timing experiment uses a separate RK45 run with `rtol=1e-11`,
`atol=1e-14` and `max_step=0.002` to obtain the reference endpoint
`(31.75561249, 3.47967132, 0.01010072)`. Each timed solver must pass its
own absolute endpoint tolerance. The table gives the observed errors and work on CPython 3.12.14.

| Solver | Maximum endpoint difference | Acceptance tolerance | Accepted steps or events | Rejected trials | RHS evaluations |
|---|---:|---:|---:|---:|---:|
| Euler | 7.45e-4 | 8e-4 | 20,000 | 0 | 20,000 |
| RK4 | 2.96e-6 | 4e-6 | 10,001 | 0 | 40,004 |
| RK45 | 7.57e-11 | 2e-9 | 3,163 | 69 | 19,393 |
| QSS1 | 3.10e-3 | 4e-3 | 116,125 | 0 | 116,126 |

Run the experiment on the target machine for raw durations, medians and
inclusive IQRs. [Timing script](../benchmarks/benchmark_argesim_c01.py)

```sh
python benchmarks/benchmark_argesim_c01.py --repeat 9 --warmup 1
```

## Task B loss-rate study

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
NumPy 2.3.5. The probe also uses mpmath for the C05 cases. [Independent equations](../scripts/benchmark_spec_probe.py) ·
[Endpoint regressions](../tests/test_argesim_c01.py)

## Task C stationary states

The analytical stationary states agree with Dymola Task C. Constant
bombardment at $p=10000$ gives $(r,m,f)=(1000,10,10)$. At $p=0$ all three
populations are zero. The test also substitutes the nonzero stationary state
back into the ODE and checks that each derivative has magnitude below
`1e-12`. [Published Dymola solution](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C01/C1-solution-Dymola.pdf)
