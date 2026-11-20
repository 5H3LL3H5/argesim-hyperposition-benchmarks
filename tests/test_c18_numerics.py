import math
import random
import unittest
from dataclasses import replace

from argesim_benchmarks.models._c18_recurrent import _sequence
from argesim_benchmarks.models.c18_nonlinear_identification import (
    C18DataSet,
    c18_correlation,
    c18_error_trend,
    fit_c18_dynamic,
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
            "dynamic_trials",
            "dynamic_selected_seed",
            "linear_validation",
            "parallel_validation",
            "dynamic_validation",
        ):
            self.assertEqual(getattr(first, field), getattr(second, field))
        self.assertNotEqual(
            first.dynamic_validation_one_step, second.dynamic_validation_one_step
        )

    def test_dynamic_restarts_are_selected_by_training_free_run(self):
        training, validation = known_system(18), known_system(19)
        seeds = (18, 19, 20)
        result = run_c18_tasks(training, validation, epochs=2)
        singles = [
            run_c18_tasks(training, validation, dynamic_seeds=[s], epochs=2)
            for s in seeds
        ]
        scores = [
            math.sqrt(
                sum(
                    (x - y) ** 2
                    for x, y in zip(training.force[2:], r.dynamic_training[2:])
                )
                / (len(training.force) - 2)
            )
            for r in singles
        ]
        best = min(range(len(seeds)), key=scores.__getitem__)
        self.assertEqual(result.dynamic_selected_seed, seeds[best])
        self.assertEqual(result.dynamic_model, singles[best].dynamic_model)
        self.assertEqual(
            (result.dynamic_fit, result.dynamic_epochs), ("output-feedback", 2)
        )
        self.assertEqual(
            result.dynamic_model, fit_c18_dynamic(training, seed=seeds[best], epochs=2)
        )
        for trial, seed, score in zip(result.dynamic_trials, seeds, scores):
            self.assertEqual(trial.seed, seed)
            self.assertAlmostEqual(trial.training_free_run_rmse, score)
        self.assertEqual(result.first_scored_sample, 2)
        self.assertAlmostEqual(
            result.dynamic_ann.validation_correlation,
            c18_correlation(validation.force[2:], result.dynamic_validation[2:]),
        )
        for invalid in ((), (18, 18), (False,), ("18",)):
            with (
                self.subTest(seeds=invalid),
                self.assertRaisesRegex(ValueError, "dynamic_seeds"),
            ):
                run_c18_tasks(training, validation, dynamic_seeds=invalid, epochs=1)

    def test_sequence_jacobian_includes_both_feedback_delays_for_every_weight(self):
        parameters = [
            0.4,
            -0.22,
            0.13,
            0.7,
            -0.01,
            0.52,
            -0.33,
            0.65,
            -0.28,
            0.46,
            0.2,
            -0.7,
            0.11,
        ]
        inputs = [math.sin(i * 0.3) for i in range(20)]
        targets = [math.cos(i * 0.4) for i in range(20)]
        _, jacobian = _sequence(parameters, inputs, targets, derivatives=True)
        for col in range(len(parameters)):
            plus, minus = parameters.copy(), parameters.copy()
            plus[col] += 1.0e-6
            minus[col] -= 1.0e-6
            ep, _ = _sequence(plus, inputs, targets, derivatives=False)
            em, _ = _sequence(minus, inputs, targets, derivatives=False)
            for row, a, b in zip(jacobian, ep, em):
                self.assertAlmostEqual(row[col], (b - a) / 2.0e-6, delta=3.0e-9)
        changed = targets[:2] + [v + 2 for v in targets[2:]]
        before, _ = _sequence(parameters, inputs, targets, derivatives=False)
        after, jac_changed = _sequence(parameters, inputs, changed, derivatives=True)
        self.assertEqual(jacobian, jac_changed)
        for a, b in zip(before, after):
            self.assertAlmostEqual(b - a, 2.0)

    def test_sequence_fit_generalizes_on_known_nonlinear_feedback_system(self):
        def recording(seed):
            rng = random.Random(seed)
            inputs = tuple(rng.uniform(-1, 1) for _ in range(120))
            outputs = [0.2, -0.1]
            for i in range(2, len(inputs)):
                outputs.append(
                    0.2
                    + 0.7
                    * math.tanh(
                        0.5 * outputs[-1]
                        - 0.2 * outputs[-2]
                        + 0.8 * inputs[i - 1]
                        - 0.3 * inputs[i - 2]
                        - 0.1
                    )
                )
            return C18DataSet(inputs, outputs)

        train, holdout = recording(45), recording(78)
        network = fit_c18_dynamic(train, seed=12, epochs=20)
        predictions = list(holdout.force[:2])
        for i in range(2, len(holdout.force)):
            predictions.append(
                network.predict_one(
                    (
                        predictions[-1],
                        predictions[-2],
                        holdout.thickening[i - 1],
                        holdout.thickening[i - 2],
                    )
                )
            )
        rmse = math.hypot(
            *(v - p for v, p in zip(holdout.force[2:], predictions[2:]))
        ) / math.sqrt(len(predictions) - 2)
        self.assertLess(rmse, 0.01)
        with self.assertRaisesRegex(ValueError, "epochs"):
            fit_c18_dynamic(train, epochs=0)

    def test_recurrent_fit_is_invariant_to_large_input_units(self):
        base = (0.95, 0.95, -0.95, 0.95, 0.9, 0.95, 0.95, 0.95)
        output = (0.0, 0.1, 0.2, 0.4, -0.1, 0.3, 0.5, 0.4)
        scaled = tuple(math.ldexp(v, 1024) for v in base)
        networks = [
            fit_c18_dynamic(C18DataSet(x, output), seed=18, epochs=4)
            for x in (base, scaled)
        ]
        for i in range(2, len(output)):
            predictions = [
                model.predict_one((output[i - 1], output[i - 2], x[i - 1], x[i - 2]))
                for model, x in zip(networks, (base, scaled))
            ]
            self.assertAlmostEqual(*predictions, delta=1.0e-9)

    def test_explicit_one_step_fit_reproduces_the_previous_training_method(self):
        training, validation = known_system(18), known_system(19)
        result = run_c18_tasks(
            training, validation, epochs=2, dynamic_fit="one-step", dynamic_seeds=[18]
        )
        rows = [
            (
                training.force[i - 1],
                training.force[i - 2],
                training.thickening[i - 1],
                training.thickening[i - 2],
            )
            for i in range(2, len(training.force))
        ]
        self.assertEqual(
            result.dynamic_model,
            fit_c18_mlp(rows, training.force[2:], hidden=10, epochs=2),
        )
        self.assertEqual((result.dynamic_fit, result.dynamic_epochs), ("one-step", 2))
        with self.assertRaisesRegex(ValueError, "dynamic_fit"):
            run_c18_tasks(training, validation, dynamic_fit="unknown")

    def test_correlation_is_invariant_to_signal_units(self):
        for exponent in (-1000, -500, 0, 500, 1000):
            scale = math.ldexp(1.0, exponent)
            signal = tuple(scale * n for n in (-2, -1, 0, 1, 2))
            self.assertAlmostEqual(c18_correlation(signal, signal), 1)
            self.assertAlmostEqual(c18_correlation(signal, (2, 1, 0, -1, -2)), -1)
        self.assertEqual(c18_correlation((1.0, 1.0), (0.0, 1.0)), 0)

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
