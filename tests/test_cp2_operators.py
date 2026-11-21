"""Contracts specific to the optional CP2 neural-operator experiment."""

import importlib.util
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(importlib.util.find_spec("numpy"), "requires the operators extra")
class ReferenceTests(unittest.TestCase):
    def test_triangle_agrees_with_independent_series(self):
        import numpy as np

        from argesim_benchmarks.experiments import cp2_fields as f

        for t in (0, *f.PROFILE_TIMES):
            x = np.array([0.031, 0.137, 0.239, 0.371])
            expected = [
                f.cp2.cp2_swinging_rope_analytical(xx, t, terms=1500) for xx in x
            ]
            np.testing.assert_allclose(f.triangle_reference(x, t), expected, atol=4e-8)

    def test_sine_and_held_out_fields(self):
        import numpy as np

        from argesim_benchmarks.experiments import cp2_fields as f

        class FirstMode:
            def normal(self, *, size):
                coefficients = np.zeros(size)
                coefficients[:, 0] = 1
                return coefficients

        x, y = f.rope_samples(1, FirstMode())
        for i, time in enumerate(f.PROFILE_TIMES):
            multiplier = np.cos(np.pi * f.ROPE.nu * time / f.ROPE.length)
            np.testing.assert_allclose(y[0, i], multiplier * x[0], atol=1e-8)
        streams = np.random.SeedSequence(2027).spawn(3)
        splits = [f.rope_samples(3, np.random.default_rng(s))[0] for s in streams]
        self.assertEqual(len({row.tobytes() for split in splits for row in split}), 9)

    def test_uniform_density_matches_existing_cavity_entry_point(self):
        import numpy as np

        from argesim_benchmarks.experiments import cp2_fields as f

        measured = f.cavity_field(np.ones((9, 9)))
        expected = f.cp2.cp2_task2_lid_driven_cavity(
            nx=9,
            iterations=f.CAVITY_STEPS,
            backend="serial",
        )
        np.testing.assert_allclose(
            measured, expected.relative_speed, rtol=0, atol=1e-14
        )


@unittest.skipUnless(
    importlib.util.find_spec("neuralop") and importlib.util.find_spec("torch"),
    "requires neuraloperator and torch",
)
class OperatorTests(unittest.TestCase):
    def test_weights_round_trip_and_physical_boundaries(self):
        import numpy as np
        import torch

        from argesim_benchmarks.experiments import cp2_operators as lab

        torch.set_num_threads(1)
        with tempfile.TemporaryDirectory() as tmp:
            for case, x in (
                ("rope", np.sin(np.linspace(0, np.pi, 65))),
                ("cavity", np.ones((17, 17))),
            ):
                model = lab.make_model(case)
                prediction = lab.predict_array(case, model, x)
                path = Path(tmp) / f"{case}.npz"
                lab.save_weights(path, case, lab.tensor_weights(model))
                restored_case, restored = lab.load_weights(path)
                self.assertEqual(restored_case, case)
                np.testing.assert_array_equal(
                    prediction, lab.predict_array(case, restored, x)
                )
                if case == "rope":
                    self.assertEqual(prediction.shape, (2, 65))
                    np.testing.assert_array_equal(prediction[:, [0, -1]], 0)
                else:
                    self.assertEqual(prediction.shape, (1, 17, 17))
                    self.assertGreaterEqual(prediction.min(), 0)
                    np.testing.assert_array_equal(prediction[0, -1], 1)

    def test_incompatible_input_is_rejected(self):
        import numpy as np

        from argesim_benchmarks.experiments import cp2_operators as lab

        for case, bad in (
            ("rope", np.ones(65)),
            ("rope", np.zeros(4)),
            ("cavity", np.ones((9, 9))),
            ("cavity", np.zeros((17, 17))),
        ):
            with self.assertRaises(ValueError):
                lab.predict_array(case, lab.make_model(case), bad)
