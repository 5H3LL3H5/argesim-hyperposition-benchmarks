"""Independent regressions for the structure-aware CP2 operators."""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AVAILABLE = all(importlib.util.find_spec(name) for name in ("scipy", "numpy"))
NEURAL = AVAILABLE and all(
    importlib.util.find_spec(name) for name in ("torch", "neuralop")
)
MAT = (
    Path(__file__).resolve().parents[1]
    / "docs/lehrbuch/studienbuch/material/cp2_genauigkeit"
)


@unittest.skipUnless(AVAILABLE, "requires NumPy and SciPy")
class FieldTests(unittest.TestCase):
    def test_sine_and_interpolated_time(self):
        import numpy as np

        from argesim_benchmarks.experiments import cp2_accuracy as a

        t, k = a.rope_fit(count=4, modes=5, step=0.25)
        x = np.linspace(0, 1, 33)
        mode = np.sin(3 * np.pi * x)
        p = a.rope_predict(mode, [0.25, 0.375], t, k)
        expected = mode * np.cos(3 * np.pi * 0.12 * 0.25)
        np.testing.assert_allclose(p[0], expected, atol=1e-14)
        np.testing.assert_allclose(
            p[1], (p[0] + mode * np.cos(3 * np.pi * 0.12 * 0.5)) / 2, atol=1e-14
        )
        with self.assertRaises(ValueError):
            a.rope_predict(mode, 8.01, t, k)
        np.testing.assert_allclose(
            a.rope_predict(np.sin(6 * np.pi * x), 0, t, k), 0, atol=1e-14
        )

    def test_signed_lbm_and_fallback_streaming(self):
        import numpy as np

        from argesim_benchmarks.experiments import cp2_accuracy as a
        from argesim_benchmarks.models import cp2_parallel_and_distributed as cp

        n = 7
        lid = 0.075
        d = 1 + np.arange(n * n).reshape(n, n) / 1000
        out = a.cavity_snapshots(d[None], lid, [1, 4])
        grid = (d[..., None] * np.array(cp.CP2_LBM_WEIGHTS)).tolist()
        for step in range(1, 5):
            grid = cp.cp2_lbm_step(grid, n, cp.cp2_lbm_relaxation(n, u0_x=lid), lid)
            if step in out:
                p = np.array(grid)
                v = np.einsum("ijk,kd->dij", p, cp.CP2_LBM_VELOCITIES) / p.sum(-1) / lid
                v[:, -1] = np.array([[1], [0]])
                np.testing.assert_allclose(out[step][0], v, rtol=1e-6, atol=3e-8)

    def test_zero_pluck_crossing_has_only_absolute_error(self):
        import numpy as np

        from argesim_benchmarks.experiments import cp2_accuracy as a

        x = np.linspace(0, 0.5, 501)
        np.testing.assert_allclose(a.pluck(x, 0.5 / (2 * 0.06), 0.5), 0, atol=1e-15)
        with self.assertRaises(ValueError):
            a.pluck(x, 0, 0)

    def test_lab_commands_reject_modified_rope_fields(self):
        import numpy as np

        cases = (
            ("cp2_feldlabor", "rope/rope-501-fields.npz", "fno", 0, "außerhalb"),
            (
                "cp2_genauigkeit",
                "saite_beispiel.npz",
                "ref",
                2,
                "Not equal to tolerance",
            ),
        )
        for lab, file, key, scale, diagnostic in cases:
            with self.subTest(lab=lab), tempfile.TemporaryDirectory() as tmp:
                copy = Path(tmp) / lab
                shutil.copytree(MAT.parent / lab, copy)
                command = [sys.executable, str(copy / "auswerten.py")]
                original = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertEqual(original.returncode, 0, original.stderr)
                path = copy / file
                with np.load(path, allow_pickle=False) as data:
                    arrays = {name: data[name] for name in data.files}
                arrays[key] *= scale
                np.savez_compressed(path, **arrays)
                result = subprocess.run(command, capture_output=True, text=True, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(diagnostic, result.stderr)


@unittest.skipUnless(NEURAL, "requires the operators extra")
class CheckpointTests(unittest.TestCase):
    def test_fine_tuning_preserves_original_rope_checkpoint_contract(self):
        import numpy as np
        import torch

        from argesim_benchmarks.experiments import cp2_operators as old

        torch.set_num_threads(1)
        case, net = old.load_weights(MAT / "saite_fno_nachtrainiert.npz")
        self.assertEqual(case, "rope")
        with np.load(MAT / "saite_beispiel.npz", allow_pickle=False) as data:
            x, truth = data["x"], data["ref"]
            initial = 0.1 * np.minimum(x / 0.5, 1 - x / 0.5)
            pred = old.predict_array(case, net, initial)
            before = np.linalg.norm(data["old"] - truth, axis=1)
        self.assertEqual(pred.shape, (2, 501))
        self.assertTrue(np.all(np.linalg.norm(pred - truth, axis=1) < before))

    def test_fixed_checkpoint_beats_affine_on_archived_field(self):
        import numpy as np
        import torch

        from argesim_benchmarks.experiments import (
            cp2_accuracy as a,
        )
        from argesim_benchmarks.experiments import (
            cp2_residual_fno as new,
        )

        torch.set_num_threads(1)
        rng = np.random.default_rng(np.random.SeedSequence(2027).spawn(3)[2])
        density = a.density_samples(17, rng.uniform(-1, 1, (1, 6)))
        ref = a.cavity_snapshots(density, 0.1, [16])[16]
        net, weights, scale = new.load(MAT / "kavitaet.npz")
        field = new.predict(net, density, weights, scale)
        with np.load(MAT / "kavitaet_beispiel.npz", allow_pickle=False) as saved:
            np.testing.assert_allclose(field[0], saved["new"], rtol=3e-5, atol=3e-7)
        inside = (slice(None), slice(None), slice(1, -1), slice(1, -1))
        self.assertLess(
            np.linalg.norm((field - ref)[inside]),
            np.linalg.norm((a.affine_predict(density, weights) - ref)[inside]),
        )
        with self.assertRaises(ValueError):
            new.predict(net, density[..., :-1], weights, scale)

    def test_parameter_checkpoint_and_bounds(self):
        import numpy as np
        import torch

        from argesim_benchmarks.experiments import cp2_parameter_fno as mod

        torch.set_num_threads(1)
        net, bank = mod.load(MAT / "kavitaet_familie.npz")
        field, _ = mod.predict(
            net, bank, np.ones((1, 21, 21), dtype="float32"), 0.0875, 12
        )
        self.assertEqual(field.shape, (1, 2, 21, 21))
        np.testing.assert_array_equal(field[:, 0, -1], 1)
        with self.assertRaises(ValueError):
            mod.predict(net, bank, np.ones((1, 21, 21)), 0.2, 12)
        with self.assertRaises(ValueError):
            mod.predict(net, bank, np.ones((1, 21, 21)), 0.1, 12.5)


if __name__ == "__main__":
    unittest.main()
