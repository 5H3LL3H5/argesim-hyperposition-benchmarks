# CP2 FNO accuracy ablation (experimental)

This study separates *measured* results from hypotheses. No improvements are claimed until the
JSON output has been generated and independently checked.

## Reproduce

Install the repository's optional neural-operator dependencies (including `neuraloperator==2.0.0`).
From the repository root:

```sh
python -m unittest tests.test_cp2_fno_ab
python -m argesim_benchmarks.experiments.cp2_fno_ab --out results/cp2-fno-ab --epochs 80 --seeds 2027 2028 2029
```

The script writes `results/cp2-fno-ab/cp2-fno-ab.json`. Output is **not** committed as
evidence by this change. Set one CPU thread and deterministic Torch algorithms. Timing
depends on hardware and is not a cross-machine performance comparison.

## Controlled variants

| Variant | Training distribution | FNO | Loss |
| --- | --- | --- | --- |
| A0 | Original eight-mode smooth data | 24 Fourier modes, width 12, 2 layers | Scaled MSE |
| B1 | 50% smooth, 50% randomized triangular plucks | A0 | Scaled MSE |
| B2 | B1 | 48 Fourier modes, width 24, 3 layers | Scaled MSE |
| B3 | B1 | A0 | Scaled MSE + 0.1 scaled spatial-gradient MSE |

All variants use 96/16/24 independent training/validation/test samples, the same seeds,
Adam learning rate 0.003, batch size 16, and best-validation-epoch checkpointing.
A0 uses the existing smooth data sampler. B1-B3 use the mixed sampler. Consequently,
**A0 and B1-B3 in-distribution test errors are not directly comparable**: their test
distributions differ. The shared canonical triangular pluck, evaluated on 65 and 501
nodes at 5 s and 8 s against the existing exact d'Alembert reference and Newmark
baseline, is the primary cross-variant comparison.

Randomized triangular plucks vary peak location, amplitude and sign. Their references
use the exact fixed-end odd-periodic d'Alembert solution. This is a zero-initial-velocity
wave problem, not a general time-dependent neural PDE solver. The canonical centered
pluck is not drawn directly by the random sampler (continuous peak distribution).

## Interpretation and limitations

- Report individual seed results, mean and spread, canonical relative L2 and maximum
  absolute displacement error, train/test times, and parameter counts.
- Do not equate a 65-node training run with a 501-node training run. This experiment
  tests **resolution transfer** from 65 to 501 nodes, not retraining on 501 nodes.
- B2 changes both spectral modes and capacity; a positive B2 result cannot attribute
  the improvement to one factor. A follow-up factorial ablation is needed.
- B3's gradient penalty emphasizes sharp transitions, but may reduce global L2
  accuracy; treat this as an empirical question.
- Validation and test splits use independent RNG streams but the same distribution;
  the canonical pluck is a separate, fixed out-of-distribution benchmark.
- No physical energy-conservation guarantee or continuous-time PDE-residual claim
  is made. Cavity and FNO vector-velocity physics are outside this rope-only study.
