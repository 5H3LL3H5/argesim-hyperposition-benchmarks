import random
import unittest

from argesim_benchmarks.catalog import BenchmarkStatus, benchmark
from argesim_benchmarks.models.c18_nonlinear_identification import (
    C18_PUBLISHED_TRANSFER,
    C18DataSet,
    C18LinearModel,
    c18_correlation,
    c18_digitized_data,
    c18_error_trend,
    fit_c18_linear,
    predict_c18_linear,
    run_c18_tasks,
)


class C18Tests(unittest.TestCase):
    def test_digitized_provenance_and_published_scale_correlations(self) -> None:
        self.assertEqual(benchmark("C18").status, BenchmarkStatus.SPECIFIED)
        training, validation = c18_digitized_data()
        self.assertEqual(len(training.force), 2000)
        self.assertEqual(len(validation.force), 2000)
        self.assertIn("digitized", training.provenance)
        model = fit_c18_linear(training)
        self.assertEqual(C18_PUBLISHED_TRANSFER, (1.586, -0.5985, 0.5289, -0.5206))
        # Apply the published coefficients without fitting to these curves.
        published = C18LinearModel(*C18_PUBLISHED_TRANSFER)
        for data, reference, refitted in (
            (training, 0.95, 0.9418),
            (validation, 0.94, 0.9331),
        ):
            self.assertEqual(
                round(
                    c18_correlation(data.force, predict_c18_linear(published, data)), 2
                ),
                reference,
            )
            self.assertAlmostEqual(
                c18_correlation(data.force, predict_c18_linear(model, data)),
                refitted,
                delta=0.0001,
            )

    def test_arx_estimator_recovers_known_system(self) -> None:
        rng = random.Random(18)
        signal = tuple(rng.uniform(-1.0, 1.0) for _ in range(500))
        output = [0.0, 0.0]
        expected = (1.2, -0.35, 0.4, -0.1)
        for index in range(2, len(signal)):
            output.append(
                expected[0] * output[-1]
                + expected[1] * output[-2]
                + expected[2] * signal[index]
                + expected[3] * signal[index - 1]
            )
        model = fit_c18_linear(C18DataSet(signal, tuple(output)))
        for actual, reference in zip(model.coefficients, expected):
            self.assertAlmostEqual(actual, reference, delta=1.0e-8)

    def test_all_identification_paths_execute_deterministically(self) -> None:
        training, validation = c18_digitized_data(sampling_hz=5)
        first = run_c18_tasks(training, validation, epochs=20)
        second = run_c18_tasks(training, validation, epochs=20)
        self.assertEqual(first, second)
        for metrics in (
            first.linear,
            first.parallel_ann,
            first.dynamic_ann,
            first.dynamic_ann_one_step,
        ):
            self.assertGreaterEqual(metrics.training_correlation, -1.0)
            self.assertLessEqual(metrics.training_correlation, 1.0)
            self.assertGreaterEqual(metrics.validation_correlation, -1.0)
            self.assertLessEqual(metrics.validation_correlation, 1.0)
        self.assertEqual(len(first.linear_training), len(training.force))
        self.assertEqual(len(first.dynamic_validation), len(validation.force))
        self.assertAlmostEqual(
            c18_error_trend((0.0, 1.0, 2.0), (0.0, 0.0, 0.0), sampling_hz=1.0),
            1.0,
        )


if __name__ == "__main__":
    unittest.main()
