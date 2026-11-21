# C09R controller and figure checks

The registered simulation uses the revised definition's 1 s controller cycle and
0.1 V input disturbance at 50,000 s. Figure 4b places the feet of the falling
and rising memberships at approximately +0.001 and −0.001 cm. Both slow rules
therefore contribute when the level is steady. The earlier implementation cut
both memberships off at zero. The original plot spans 0.1 cm over 644 pixels.
The six-to-seven-pixel overlap on either side of the centre fixes the feet to
about one pixel. [Revised definition, pp. 53–56](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C09/C9R-revised-definition.pdf)

## Registered closed-loop run

The comparison reads the solid second-tank trace in the original bitmaps.
The measurement band is ±1 cm. A vertical pixel represents 0.299 cm in
Figure 7 and 0.299 cm in Figure 9. Each window includes both endpoints on
the runner's 100 s output grid. The two plateau measurements use the median.
[Simulink solution, p. 76](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C09/C9R-solution-MATLAB-Simulink-Fuzzy.pdf)

| Controller and observable | Window (s) | Figure (cm) | Model (cm) | Within band |
|---|---:|---:|---:|---|
| I-FC2 peak, Fig. 7 | 24,000–28,000 | 62.985 | 59.999 | No |
| P-FC plateau, Fig. 9 | 44,000–46,000 | 40.419 | 40.282 | Yes |
| P-FC plateau, Fig. 9 | 54,000–56,000 | 41.916 | 53.585 | No |

## What the valve trace explains

**P-FC disturbance.** Figure 6 provides a separate controller from the P-FC
comparison. Before and after the disturbance its integral action restores
the same 0.40 m level. Its valve command drops from 1.7134 to 1.5155 in
plot units. Before the disturbance the mass balance gives
`u = c2 v2 sqrt(h2) / c1`, or 0.09999 V per plotted unit. At equal steady
levels the required total inflow is the same. The observed drop therefore
implies an effective additive input of about 0.0198 V. Applying that value to
the P-FC model predicts **41.999 cm** for the held-out post-disturbance window.
This agrees with the plot and identifies incompatible effective disturbance
magnitudes. The definition explicitly prescribes 0.1 V. Its value remains the
registered default. The authors' exact block gain and step settings are unknown.

**I-FC2 peak.** A separate replay reads the valve trajectory from the lower
panel of Figure 7 and integrates the two tank balances up to 28,000 s. It
uses the chart-coordinate convention in which the printed coefficients operate
on levels in centimetres and the plotted valve ordinate. Expressing those
equations in metres and the inferred physical voltage multiplies the SI level
rates by 0.1. The digitizer linearly interpolates the original pixel columns.
With empty tanks at startup, the replay reaches **63.126 cm** in the peak
window. This shows the plant can produce the observed overshoot when driven by
the recorded command under that convention. The registered closed-loop
controller still misses it. The original FIS, output discretization and signal
scales would allow a like-for-like comparison of the valve command itself.
[Block diagram, controller surfaces and traces](https://www.sne-journal.org/fileadmin/user_upload_sne/benchmarks/C09/C9R-solution-MATLAB-Simulink-Fuzzy.pdf)

## Reproduction

C09 is `implemented`. The normal validation command reports each measurement, tolerance and outcome.
Strict mode exits unsuccessfully when any figure check is outside its band.
The optional PDF probe uses PyMuPDF, Pillow and NumPy and verifies the source
SHA-256 before reading the original pixels.

```sh
python -m argesim_benchmarks run C09 validate
python -m argesim_benchmarks run C09 validate --kwargs-json '{"require_figure_match":true}'
python scripts/c09_figure_probe.py C9R-solution-MATLAB-Simulink-Fuzzy.pdf
```
