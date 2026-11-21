# Quantized solvers on switched, constrained and sampled ARGESIM models

**Repository technical report · 21 November 2026**

Can a higher-order quantizer take fewer steps and still detect every physical event? On the C21 bouncing ball, QSS3 and QSS4 recover both analytic impact times once the event detector searches within a step. The wider comparison gives a different answer for each model. All 18 named quantized methods meet the target on at least one setting for the sampled tank, the short robot transient and the elastic contact chain. None meets the declared targets for the stiff C05 switch or the linear C13 crane within the tested grid and budgets. For the diode circuit, a separate residual-form solver agrees with both explicit reductions through all 149 switches.

[Method explanations](SOLVER_METHODS.md) · [Printable report and methods appendix](ARGESIM_SOLVER_STUDY.pdf) · [Measured configurations](evidence/qss-extension.csv)

## What was measured

Each of eight cases has 57 configurations. The 18 QSS method names each receive three quanta: a component's fixed physical scale multiplied by 0.005, 0.001 or 0.0002. Euler, RK4 and RK45 each have one setting per case. eLIQSS1 and CheQSS1 have the same mathematical update. CQSS1 was attempted everywhere, including dissipative problems outside its published geometric guarantee.

| Case | Interval and observables | Reference |
|---|---|---|
| C03 amplifier | Ideal switch, all four states at 5 and 10 µs. Tolerance 0.001 times the component scale. | Separately written affine circuit matrices and their exponentials in each phase. Finite ramps are outside this run. |
| C05 switch | 3.5 s, three switching times within 1 ms plus both terminal states within 0.006. | The model's analytical two-mode solution. Switch count must agree before timing error is evaluated. |
| C07 pendulum | First 2 s of A(i), all pin crossings within 1 ms and terminal angle and angular velocity within 0.001 rad and 0.004 rad/s. | Independently written equations, pin resets and high-accuracy DOP853 integration. |
| C09 tanks | 16 one-second P-FC updates, disturbance from 4 s, both levels at every sample within 0.5 mm. | DOP853 with the same controller and plant. This measures integration error for that input sequence. |
| C11 robot | Nine states at 0.1 ms, before current limitation, within 0.001 times component scales. | SciPy Radau with the same right-hand side. Later constrained motion and controller performance remain open. |
| C12 spheres | Four equal masses, elastic contacts in order at 1, 2 and 3 s. At 4 s only the last sphere moves. Tolerance 0.001 for each time and speed. | Analytic momentum transfer in the reduced free-flight and instantaneous-reset model. |
| C13 crane | Linear Task A, load pulse −800 N, five states at 4, 7 and 15 s. Tolerance 0.001 times component scales. | Independently transcribed affine matrices with exact phase propagation up to matrix-exponential roundoff. |
| C21 ball | Two impacts before 5 s, each within 1 ms. Regression tests also check rebound and final height. | Analytical no-drag flight and restitution, initial height 10 m. |

The score is the largest absolute error divided by that observable's tolerance. A run passes at a score of one or less with the complete event sequence. An event-count mismatch, integrator exception or time budget expiry has its own status. Targets apply at the listed observations. A trajectory can deviate between observations. Case-specific fixed steps, scales, partitions and reference tolerances are recorded in the [executable protocol](../benchmarks/benchmark_solver_extension.py).

## All methods and cases

Each QSS cell counts passing quantum levels out of three. Each classical cell counts passes out of one. Zero means every setting was attempted and none qualified. The raw data distinguish accuracy, event and execution failures.

| Method | C03 | C05 | C07 | C09 | C11 | C12 | C13 | C21 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qss1 | 0 | 0 | 1 | 3 | 3 | 3 | 0 | 1 |
| qss2 | 0 | 0 | 1 | 3 | 3 | 3 | 0 | 3 |
| qss3 | 0 | 0 | 1 | 3 | 3 | 3 | 0 | 3 |
| qss4 | 0 | 0 | 2 | 3 | 3 | 3 | 0 | 3 |
| cqss1 | 0 | 0 | 3 | 3 | 3 | 3 | 0 | 3 |
| liqss1 | 0 | 0 | 0 | 3 | 2 | 2 | 0 | 0 |
| liqss2 | 0 | 0 | 1 | 2 | 3 | 3 | 0 | 3 |
| liqss3 | 0 | 0 | 1 | 2 | 2 | 3 | 0 | 0 |
| mliqss1 | 0 | 0 | 0 | 3 | 3 | 2 | 0 | 0 |
| mliqss2 | 0 | 0 | 1 | 2 | 3 | 3 | 0 | 3 |
| mliqss3 | 0 | 0 | 1 | 2 | 2 | 3 | 0 | 0 |
| eliqss1 | 1 | 0 | 3 | 2 | 3 | 2 | 0 | 3 |
| eliqss2 | 0 | 0 | 1 | 2 | 3 | 3 | 0 | 3 |
| eliqss3 | 1 | 0 | 2 | 2 | 2 | 3 | 0 | 0 |
| cheqss1 | 1 | 0 | 3 | 2 | 3 | 2 | 0 | 3 |
| cheqss2 | 0 | 0 | 1 | 2 | 3 | 3 | 0 | 3 |
| cheqss3 | 0 | 0 | 1 | 2 | 2 | 3 | 0 | 0 |
| liqss-bdf | 0 | 0 | 3 | 2 | 3 | 3 | 0 | 3 |
| euler | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 0 |
| rk4 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 |
| rk45 | 1 | 0 | 1 | 1 | 1 | 1 | 1 | 1 |

Of 456 configurations, 222 pass, 151 complete outside tolerance, 20 return the wrong event count, 46 time out and 17 stop with a solver error or work limit. All 20 event mismatches occur on C05.

## Cost at the required accuracy

Each entry gives the fastest observed median among passing configurations in its group. The QSS work columns report accepted updates and right-hand-side evaluations as counted by the backend. Terminal interpolation, force changes and physical resets can advance the solution even when a quantizer reports zero accepted updates.

| Case | QSS names passing | Fastest QSS | Factor | Median ms | Updates / RHS | Fastest classical, ms |
|---|---:|---|---:|---:|---:|---|
| C03 | 3/18 | eliqss3 | 0.0002 | 30 | 91 / 2458 | rk45, 65.6 |
| C05 | 0/18 | — | — | — | — | — |
| C07 | 16/18 | qss4 | 0.001 | 6.29 | 28 / 345 | rk45, 12.3 |
| C09 | 18/18 | qss2 | 0.0002 | 0.754 | 0 / 48 | rk45, 1.77 |
| C11 | 18/18 | qss2 | 0.005 | 0.469 | 6 / 21 | rk45, 0.475 |
| C12 | 18/18 | qss2 | 0.0002 | 0.433 | 0 / 36 | rk45, 1.09 |
| C13 | 0/18 | — | — | — | — | rk45, 30 |
| C21 | 12/18 | qss3 | 0.005 | 0.633 | 0 / 66 | rk45, 18.2 |

Three measured solves after one warm-up give a local median. The order of configurations was shuffled with seed 71. Reported times include case-specific integration, resets and extraction of observables. Reference construction and scoring occur outside the timed region. Each case solve has a two-second wall-clock cap per repetition. Individual integrator calls receive a 40,000-step or quantizer-event limit. These limits can favour a method that reaches a moderate target quickly. They also make timeouts machine-dependent. Several close timing pairs, especially on C11, do not support a speed ranking. RK45 often achieves substantially smaller errors than the acceptance threshold.

## Interpretation by model

**C03 and C05 illustrate two different stiffness problems.** On the ideal amplifier eLIQSS3 meets the target in about 30 ms at the finest quantum. The two other qualifying QSS names, eLIQSS1 and CheQSS1, share their first-order construction. On C05 the three classical methods exhaust their step limits. Of configurations that finish with the expected number of events, eLIQSS1 comes closest at 6.62 times the allowed error. Frequent spurious switches in other runs would be hidden by a terminal-state-only score. The negative result is conditional on the chosen quanta, steps and budgets.

**C07 and C21 expose the cost of missing a reset.** Sixteen QSS methods meet C07's combined timing and terminal-state target. On C21 the historical high-order runs detected the first impact at about 1.42784 s and ended below the floor. The post-impact trajectory could rise and fall during one accepted step. Searching the cubic coordinate interpolant on each side of its extrema recovers the second impact at about 3.997961 s for QSS3 and QSS4 on all three levels. The event count regression complements the millisecond timing threshold. Accuracy on a no-drag parabola does not establish accuracy on arbitrary guard functions.

**C09, C11 and C12 are easy for different reasons.** The one-second controller sampling already divides C09 into short smooth segments. Model-side input and FIS assumptions still determine agreement with the published tank levels. C11 tests just the initial 0.1 ms of a nine-state model. C12's reduced free-flight sections have constant velocities, so QSS2 can propagate between successive contacts without a quantizer update. Extending that result to compliant collisions would require another experiment. [C09 published-figure comparison](C09_FIGURE_CHECKS.md)

**C13 rewards conventional time stepping at these settings.** RK4 and RK45 meet the 15 state observations. The closest QSS run, QSS3 at factor 0.0002, misses the target by a factor of 2.20. The existing 2,000 s crane endpoint reference answers a different question. It cannot establish the short-window tolerance for a new solver. [Crane reference analysis](C13_REFERENCE_ANALYSIS.md)

## A direct DAE check on the C21 diode

We supplied the residual solver with Kirchhoff's equations and the piecewise Shockley current law. Its differential states are inductor current and capacitor voltage. Diode voltage is an algebraic unknown. The two existing hybrid models instead solve for voltage or current through separate explicit reductions. Both reached 500 µs. At 75,960 distinct requested times the direct trajectory covers both models' native timestamps plus a uniform grid. IDAS independently yields 149 sign changes by bracketing the sampled diode voltage. The registered hybrid transitions supply the comparison times.

| Largest difference against either reduction | Measured | Acceptance limit |
|---|---:|---:|
| Inductor current | 9.76 × 10⁻¹¹ A | 10⁻⁷ A |
| Capacitor voltage | 1.90 × 10⁻¹⁰ V | 10⁻⁵ V |
| Diode voltage | 2.09 × 10⁻⁹ V | 10⁻⁵ V |
| Corresponding switch time | 9.83 × 10⁻¹⁴ s | 2 × 10⁻⁸ s |

Switch-time differences compare interpolated numerical outputs. The dense sampling grid includes the hybrid solver's own timestamps, which improves bracketing near those transitions. The largest sampled residual in the scaled DAE equations was 2.20 × 10⁻¹⁰ (rounded upward). This circuit and a manufactured nonlinear constrained solution exercise the regular index-one interface. Higher-index mechanisms and arbitrary mechanical contact laws require additional formulation work. [Circuit equations and criteria](../scripts/c21_dae_reference.py) · [Exact measurements](evidence/c21-idas.json) · [API and manufactured-solution tests](../tests/test_dae.py)

## Coverage and reproduction

The earlier 399 configurations at commit `8332be4d` cover C01-A, C15-A, C17R-ODE, C21-ball, damped and undamped CP1 oscillators, and a three-node CP2 rope. Its eight-second budget and denser trajectory checks differ from this extension. The two datasets together cover **13 distinct families**. C21 appears in both. C19R still needs an experiment that varies the spatial grid separately from the time solver. C02, C04, C06, C08, C10, C14, C16, C18, C20 and C22 primarily involve discrete events, sampled recurrences, agents or identification. Their registered main tasks have no common continuous integrator to exchange. All 24 families have a status in the [coverage catalog](../ARGESIM_COVERAGE.md).

To reproduce the extension on POSIX, run from the repository root. The recorded environment used CPython 3.12.14, NumPy 2.3.5, SciPy 1.17.0 and CasADi 3.8.2 on a Linux x86-64 Xeon Platinum 8573C. Set one BLAS thread. Compare scores, event counts and work counters before wall times.

```sh
python -m pip install '.[dae]' numpy scipy
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python benchmarks/benchmark_solver_extension.py --output extension.csv
python scripts/c21_dae_reference.py
python -m unittest discover -s tests -p test_hybrid_runtime.py
python -m unittest discover -s tests -p test_dae.py
```

[Raw extension measurements](evidence/qss-extension.csv) · [Historical matrix](evidence/qss-baseline.csv) · [Historical scripts, raw runs and metadata](evidence/qss-baseline-reproduction.zip) · [Solver mechanisms, assumptions and primary sources](SOLVER_METHODS.md)
