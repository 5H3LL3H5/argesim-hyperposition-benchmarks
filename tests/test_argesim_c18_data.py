import hashlib
import tempfile
import unittest
from pathlib import Path

from argesim_benchmarks.models.c18_nonlinear_identification import (
    C18_FIGURE_PDF_SHA256,
    C18DataSet,
    c18_digitized_data,
    load_c18_csv,
    run_c18_tasks,
)
from argesim_benchmarks.runner import _suite_arguments


class C18DataTests(unittest.TestCase):
    def test_missing_data_are_never_silently_reconstructed(self):
        training, validation = c18_digitized_data(sampling_hz=5)
        for args in ({}, {"training": training}, {"validation": validation}):
            with (
                self.subTest(args=tuple(args)),
                self.assertRaisesRegex(ValueError, "both training and validation"),
            ):
                run_c18_tasks(**args, epochs=1)
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            run_c18_tasks(training, validation, use_digitized=True)
        self.assertTrue(_suite_arguments("smoke")[("C18", "all")]["use_digitized"])
        self.assertNotIn(("C18", "all"), _suite_arguments("definition"))

    def test_data_are_immutable_snapshots(self):
        thickening = [0, 1, 2, 3, 4]
        data = C18DataSet(thickening, [1, 2, 3, 4, 5])
        thickening[0] = 99
        self.assertEqual(data.thickening, (0.0, 1.0, 2.0, 3.0, 4.0))
        self.assertIsInstance(data.force, tuple)

    def test_mixed_sampling_rates_and_digitized_sources_are_rejected(self):
        training, validation = c18_digitized_data(sampling_hz=5)
        other_rate = C18DataSet(
            validation.thickening, validation.force, sampling_hz=100
        )
        with self.assertRaisesRegex(ValueError, "sampling rates"):
            run_c18_tasks(training, other_rate)
        other_source = C18DataSet(
            validation.thickening, validation.force, sampling_hz=5
        )
        with self.assertRaisesRegex(ValueError, "cannot be mixed"):
            run_c18_tasks(training, other_source)

    def test_results_carry_both_data_identities(self):
        training, validation = c18_digitized_data(sampling_hz=5)
        result = run_c18_tasks(training, validation, epochs=1)
        self.assertEqual(result.training_data.kind, "digitized")
        self.assertEqual(result.validation_data.sampling_hz, 5)
        self.assertEqual(result.training_data.samples, len(training.force))
        self.assertNotEqual(
            result.training_data.signal_sha256, result.validation_data.signal_sha256
        )
        self.assertEqual(len(result.training_data.signal_sha256), 64)
        self.assertEqual(result.training_data.source_sha256, C18_FIGURE_PDF_SHA256)
        self.assertEqual(result.validation_data.source_sha256, C18_FIGURE_PDF_SHA256)

    def test_vector_figure_grid_preserves_endpoints_and_sub_200_ms_structure(self):
        training, validation = c18_digitized_data()
        low, _ = c18_digitized_data(sampling_hz=5)
        double, _ = c18_digitized_data(sampling_hz=200)
        self.assertEqual(len(low.force), 100)
        self.assertEqual(low.force, training.force[::20])
        self.assertEqual(double.force[::2], training.force)
        self.assertEqual((training.force[0], validation.force[0]), (0.298535, 0.010657))
        self.assertEqual(
            (training.force[-1], validation.force[-1]), (0.036499, 0.135793)
        )
        linear_midpoint = (training.force[0] + training.force[20]) / 2
        self.assertGreater(abs(training.force[10] - linear_midpoint), 0.05)

    def test_distinct_filenames_cannot_turn_training_into_validation(self):
        header = "time_s,thickening,force\n"
        with tempfile.TemporaryDirectory() as directory:
            a, b = (
                Path(directory) / f"{name}.csv" for name in ("training", "validation")
            )
            a.write_text(header + "".join(f"{i / 100},{i},{2 * i}\n" for i in range(8)))
            b.write_text(
                header
                + "".join(f"{i / 100:.2f},{i:.1f},{2 * i:.1f}\n" for i in range(8))
            )
            self.assertNotEqual(
                load_c18_csv(a).source_sha256, load_c18_csv(b).source_sha256
            )
            with self.assertRaisesRegex(ValueError, "distinct recording"):
                run_c18_tasks(a, b, epochs=1)

    def test_csv_preserves_values_and_checks_byte_identity(self):
        raw = (
            b"time_s,thickening,force\n0,1,2\n0.01,2,3\n0.02,3,4\n0.03,4,5\n0.04,5,6\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "measurement.csv"
            path.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            data = load_c18_csv(path, expected_sha256=digest)
            self.assertEqual(data.force, (2, 3, 4, 5, 6))
            self.assertEqual(data.sampling_hz, 100)
            self.assertEqual(data.source_sha256, digest)
            self.assertEqual(data.kind, "csv")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                load_c18_csv(path, expected_sha256="0" * 64)

    def test_csv_rejects_gaps_duplicate_times_and_nonfinite_values(self):
        cases = (
            "time_s,thickening,force\n0,1,2\n0.02,2,3\n",
            "time_s,thickening,force\n0,1,2\n0,2,3\n",
            "time_s,thickening,force\n0,nan,2\n",
            "time_s,thickening,force\n0,1,inf\n",
            "time_s,thickening,force\n0,1,2,3\n",
            "time_s,thickening,thickening\n0,1,2\n",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.csv"
            for raw in cases:
                path.write_text(raw)
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    load_c18_csv(path)


if __name__ == "__main__":
    unittest.main()
