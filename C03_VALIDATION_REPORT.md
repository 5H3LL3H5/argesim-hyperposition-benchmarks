# ARGESIM C03 Implementation Evidence

## Definition transcription

The four-state Class-E amplifier uses `VDC=5`, `L1=79.9 µH`, `C2=17.9 nF`,
`L3=232 µH`, `C4=9.66 nF`, `RL=52.4 Ω`, `RON=0.05 Ω`, `ROFF=5 MΩ`, a
10 µs period, 50% duty cycle, and a 1 fs default rise/fall time. The solver
segments every run at the beginning and end of each switching ramp so even the
1 fs transition is represented as an explicit integration interval.

## Task A reference comparison

The independent Dymola/Simulink solutions publish these eigenvalue groups:

- ON: approximately `-1.117e9`, `-625.8`, and
  `-1.1304e5 ± 6.5835e5 i`;
- OFF: approximately `-5.4708e4 ± 1.0408e6 i` and
  `-5.8228e4 ± 5.3275e5 i`.

Committed tests compare the implementation against those values with explicit
tolerances and also verify stability of every root. This comparison caught and
corrected the former `RL=38.6 Ω` transcription error.

## Tasks B and C

Task B integrates 0–100 µs from the zero state. Task C starts from Task B's final
state and integrates 0–9 µs for 1 fs, 10 ps, 1 ns, and 100 ns rise/fall times.
The implementation uses the repository's own event-aligned RK45 solver; it does
not use SciPy.

## Evidence boundary

Task A checks the published eigenvalues. An independent affine matrix exponential checks the ideal-switch trajectory at all 20 half-cycle boundaries. For Task C, an independent calculation uses Radau on every resistance ramp in normalized local time and a matrix exponential during each constant interval. Tests compare all four state components at 9 µs for 1 fs, 10 ps, 1 ns and 100 ns ramps, starting from the end of Task B. These controls qualify the listed cases for `validated`. [Numerical comparisons](docs/PUBLISHED_REFERENCE_CHECKS.md)
