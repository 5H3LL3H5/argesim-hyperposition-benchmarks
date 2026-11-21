# C13R crane revisions, linear reference and braking

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

The archived JSON has SHA-256
`692e8bf3e33296c1308ba287fee09275085e5a382023f650ae069ca05b234115`.
The archive records both damping values, the solver version and tolerances.
[Probe source](../scripts/c13_reference_probe.py)

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

The large ±294 versus ±299 m mismatch is a definition
revision mismatch, with a smaller unresolved difference to the old published
solution. No implementation parameter was changed to fit the old table. The older shared-equation check alone cannot establish independent validation of the 2007 definition.

## Independent Task A reference and controlled braking

For the revised 2007 parameters, the independent linear reference evolves the
absolute cart and load coordinates, their two velocities and motor force. The
linearized cable acts as a horizontal spring of stiffness `k = m_load g / r`.
Cart force is `k (x_load − x_cart) − d_cart v_cart + f_motor`, and load force
is `−k (x_load − x_cart) − d_load v_load + f_disturbance`. A sixth, constant
coordinate represents the forcing. Four SciPy matrix exponentials propagate
the state across the switches at 4, 7 and 15 s. The comparison uses load
position at 2000 s and an absolute tolerance of `1e-5 m`.

| Disturbance (N) | Reference (m) | Absolute error (m) |
|---:|---:|---:|
| −750 | 299.3615227886 | 1.16e-8 |
| −800 | −0.0057068688 | 2.51e-9 |
| −850 | −299.3729365263 | 1.68e-8 |

`python scripts/benchmark_spec_probe.py` regenerates these values. The unit
suite checks the three endpoints without SciPy. The catalog's `validated`
status applies to this linear Task A case.

Task B and C both engage the holding brake after more than 3.0 continuous
seconds below 0.01 N. At 0.1 s per sample, a stationary start leaves the brake
open at 3.0 s and engages it at 3.1 s. The car damping then becomes
100,000 kg/s and the applied force command becomes zero. A new demand can
release the holding brake. Only Task C latches an emergency after crossing
either position limit. Controlled-plant tests cover the switching instants and
damping. Independent revised nonlinear and closed-loop reference trajectories
remain outstanding. [C13R definition, pp. 50–52](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C13/C13-definition-2.pdf)

In the prescribed 60 s Task B motion, the holding condition is never met.
It records zero active samples out of 601 even after the fix. The stationary
test exercises the condition directly and verifies the damping in the real
plant. The nominal Task C trajectory records 524 samples with the latched
emergency brake active.
