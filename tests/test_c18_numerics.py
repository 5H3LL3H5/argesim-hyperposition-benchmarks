import math
import random
import unittest
from dataclasses import replace

from argesim_benchmarks.models.c18_nonlinear_identification import (
    C18DataSet,
    c18_correlation,
    c18_error_trend,
    fit_c18_linear,
    fit_c18_mlp,
    run_c18_tasks,
)


def known_system(seed, scale=1.0):
    rng = random.Random(seed)
    signal = tuple(scale * rng.uniform(-1, 1) for _ in range(100))
    output = [0.0, 0.0]
    for i in range(2, len(signal)):
        output.append(
            1.2 * output[-1] - 0.35 * output[-2] + 0.4 * signal[i] - 0.1 * signal[i - 1]
        )
    return C18DataSet(signal, tuple(output))


class C18NumericsTests(unittest.TestCase):
    def test_arx_units_do_not_create_false_singularities(self):
        for scale in (1e-12, 1.0, 1e12):
            model = fit_c18_linear(known_system(18, scale), ridge=0)
            for coefficient, expected in zip(
                model.coefficients, (1.2, -0.35, 0.4, -0.1)
            ):
                self.assertAlmostEqual(coefficient, expected, delta=1e-11)

    def test_rank_deficiency_and_regularization_are_explicit(self):
        data = C18DataSet((0.0,) * 8, (0.0,) * 8)
        self.assertEqual(fit_c18_linear(data).coefficients, (0.0,) * 4)
        with self.assertRaisesRegex(ValueError, "rank-deficient"):
            fit_c18_linear(data, ridge=0)
        for ridge in (-1, math.nan, math.inf):
            with self.subTest(ridge=ridge), self.assertRaises(ValueError):
                fit_c18_linear(data, ridge=ridge)

    def test_held_out_outputs_never_train_or_feed_free_run(self):
        training, validation = known_system(18), known_system(19)
        changed = replace(
            validation,
            force=validation.force[:2]
            + tuple(
                value + math.sin(i) for i, value in enumerate(validation.force[2:])
            ),
        )
        first = run_c18_tasks(training, validation, epochs=2)
        second = run_c18_tasks(training, changed, epochs=2)
        for field in (
            "linear_model",
            "parallel_model",
            "dynamic_model",
            "linear_validation",
            "parallel_validation",
            "dynamic_validation",
        ):
            self.assertEqual(getattr(first, field), getattr(second, field))
        self.assertNotEqual(
            first.dynamic_validation_one_step, second.dynamic_validation_one_step
        )

    def test_nonfinite_metrics_and_neural_training_inputs_are_rejected(self):
        for bad in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                c18_correlation((0.0, bad), (0.0, 1.0))
            with self.assertRaises(ValueError):
                c18_error_trend((0.0, bad), (0.0, 1.0), sampling_hz=100)
            with self.assertRaises(ValueError):
                fit_c18_mlp(((0.0,), (bad,)), (0.0, 1.0), hidden=2)
            with self.assertRaises(ValueError):
                fit_c18_mlp(((0.0,), (1.0,)), (0.0, bad), hidden=2)
            with self.assertRaises(ValueError):
                fit_c18_mlp(((0.0,), (1.0,)), (0.0, 1.0), hidden=2, learning_rate=bad)
        for bad in (True, 1.5, 0):
            with self.assertRaises(ValueError):
                fit_c18_mlp(((0.0,), (1.0,)), (0.0, 1.0), hidden=bad)


if __name__ == "__main__":
    unittest.main()
