# C13R Task A: published 2006 result and revised 2007 definition

## Sources and exact comparison

- [SNE 16/1 (2006), revised C13 definition, printed p. 28](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_16_1/sne.16.1.pdf): Table of parameters gives load friction `d_l = 0.01 kg/s`, car friction `d_c = 0.5 kg/s`, masses 10 and 100 kg. Task A on printed p. 29 prescribes `f_cDesired = 160 N` over 0–15 s, `f_d = Dest` over 4–7 s and positions near 2000 s.
- [SNE 16/1 (2006), Modelica/Dymola solution, printed p. 30](https://www.sne-journal.org/fileadmin/user_upload_sne/SNE_Issues_OA/SNE_16_1/sne.16.1.pdf): Table 1 prints the Task-A values below. Its controlled examples use a 10 ms controller cycle; Task A has no controller or brake.
- [SNE 17/1 (2007), revised C13R definition, printed pp. 50 and 52](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C13/C13-definition-2.pdf): Table 1 changes load friction to `d_l = 0.001 kg/s`, while Task A retains the force schedule. Table 3 gives a 0.1 s controller cycle for the controlled tasks. The implementation follows this later parameter set.

The 2006 published result is therefore **not an oracle for the 2007 parameter set**. The 2007 table prints the load mass symbol as `m_c` in one row; the stated 100 kg value and the equations distinguish it from the 10 kg car mass. This table-label issue is not used to alter the model.

| `Dest` (N) | 2006 published linear (m) | 2006 published nonlinear (m) | SciPy with `d_l=0.01`: linear / nonlinear (m) | SciPy with `d_l=0.001`: linear / nonlinear (m) |
|---:|---:|---:|---:|---:|
| -750 | 294.075 | 294.041 | 294.084453 / 294.084453 | 299.361523 / 299.361523 |
| -800 | -0.005 | 0.008 | -0.004850 / -0.004850 | -0.005707 / -0.005707 |
| -850 | -294.096 | -294.112 | -294.094152 / -294.094152 | -299.372937 / -299.372937 |

The numerical reproduction uses the project's linear and nonlinear right-hand
sides with **SciPy 1.17.0 DOP853** as a second integration engine, `rtol=2e-13`,
`atol=2e-14`, `max_step=1 s`, switching exactly at 4, 7 and 15 s, and ending
at 2000 s. Its full precision output is
[`evidence/c13-reference-20260928.json`](evidence/c13-reference-20260928.json).
Run from the repository root with Python 3.12 and SciPy 1.17.0:

```bash
PYTHONPATH=. python scripts/c13_reference_probe.py > c13-reference.json
sha256sum c13-reference.json
```

The archived JSON SHA-256 is
`692e8bf3e33296c1308ba287fee09275085e5a382023f650ae069ca05b234115`;
the probe script SHA-256 is
`9b2bb9771327009ce5783ebf47536ef8bb4a6eb8b10840e848b02b72ae06239e`.
These checksums identify repository artifacts, **not** the remotely hosted PDFs.

## Analytic and numerical checks

The motor's first-order response integrates to the full rectangular desired
force pulse over the complete horizon. Thus the total applied horizontal
impulse is `160*15 + 3*Dest = +150, 0, -150 N s`. Ignoring the small load
friction, division by car damping `0.5 kg/s` predicts roughly `+300, 0,
-300 m`. The *linear* model also has exact midpoint symmetry:
`x(-750) + x(-850) = 2*x(-800)` for zero initial state. Both high-accuracy
runs satisfy this relation at the reported precision.

The 2007 values agree with the existing implementation's linear output to
about `2.4e-9 m`. The existing nonlinear RK45 result differs from DOP853 by
about `0.00029–0.00032 m`; this is small relative to the roughly `5.28 m`
change from the revision of `d_l`. The 2006 DOP853 values still differ from
the printed Modelica values by up to `0.0435 m`. This remaining difference is
not explained by the revision alone; solver tolerances, model realization and
rounding in the old solution remain possible causes. The SciPy probe shares
the implementation's equations, so it verifies numerical integration, not an
independent derivation of the physics.

**Classification:** the large ±294 versus ±299 m mismatch is a definition
revision mismatch, with a smaller unresolved difference to the old published
solution. No implementation parameter was changed to fit the old table. C13
remains `implemented`; this analysis alone cannot establish independent
validation of the 2007 definition.
