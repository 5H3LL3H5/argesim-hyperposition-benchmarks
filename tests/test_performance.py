"""Contract tests for isolated diagnostic timing and evidence artifacts."""

import json
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from hashlib import sha256
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, current_thread, main_thread
from unittest.mock import Mock, patch

from argesim_benchmarks.cli import main
from argesim_benchmarks.performance import measure_task, run_performance
from argesim_benchmarks.runner import CONTRACTS


class PerformanceTests(unittest.TestCase):
    def test_parallel_runs_cannot_both_reserve_the_same_directory(self):
        started, release = Event(), Event()

        def simulated_worker(*_args, **_kwargs):
            if current_thread() is not main_thread():
                started.set()
                self.assertTrue(release.wait(timeout=10))
            return Mock(stdout=json.dumps({"status": "passed", "error": None}))

        with TemporaryDirectory() as directory, patch(
            "argesim_benchmarks.performance._git_sha", return_value="a" * 40,
        ), patch(
            "argesim_benchmarks.performance.subprocess.run", side_effect=simulated_worker,
        ) as worker, ThreadPoolExecutor(max_workers=1) as pool:
            path = Path(directory)
            first = pool.submit(
                run_performance, output_dir=path, profile="smoke",
                benchmarks=("C01",), tasks=("C01:C",),
            )
            try:
                self.assertTrue(started.wait(timeout=10))
                with self.assertRaisesRegex(ValueError, "already reserved"):
                    run_performance(
                        output_dir=path, profile="smoke",
                        benchmarks=("C05",), tasks=("C05:validate",),
                    )
            finally:
                release.set()
            report = first.result(timeout=10)
            self.assertEqual(worker.call_count, 1)
            self.assertEqual(json.loads((path / "manifest.json").read_text()), report)
            self.assertEqual(sorted(file.name for file in path.iterdir()),
                             ["C01-C.json", "manifest.json"])

    def test_repetitions_are_odd_and_at_least_nine(self):
        with TemporaryDirectory() as directory:
            for repetitions in (0, 8, 10):
                with self.subTest(repetitions=repetitions), self.assertRaises(ValueError):
                    run_performance(output_dir=Path(directory), repetitions=repetitions)

    def test_parity_failure_never_produces_timing_summary(self):
        results = [1, 1, 2]
        with patch.object(CONTRACTS["C01"], "run", side_effect=results):
            record = measure_task("C01", "C", profile="smoke", warmup=1,
                                  repetitions=9)
        self.assertEqual(record["status"], "failed")
        self.assertIn("timed repetition 1", record["error"])
        self.assertEqual(len(record["timing"]["raw_seconds"]), 1)
        self.assertIsNone(record["timing"]["median_seconds"])
        self.assertIsNone(record["timing"]["iqr_seconds"])
        self.assertIsNone(record["validation"]["passed"])

    def test_cli_writes_checked_artifacts_with_nine_raw_samples(self):
        with TemporaryDirectory() as root:
            output_dir = Path(root) / "evidence"
            stdout = StringIO()
            with redirect_stdout(stdout):
                status = main([
                    "run-performance", "--profile", "smoke",
                    "--benchmark", "C01", "--task", "C01:C",
                    "--output-dir", str(output_dir),
                ])
            self.assertEqual(status, 0)
            manifest = json.loads((output_dir / "manifest.json").read_text())
            self.assertEqual((manifest["passed"], manifest["failed"]), (1, 0))
            entry = manifest["artifacts"][0]
            data = (output_dir / entry["path"]).read_bytes()
            self.assertEqual(sha256(data).hexdigest(), entry["sha256"])
            record = json.loads(data)
            self.assertEqual(record["status"], "passed")
            self.assertFalse(record["official_performance"])
            self.assertEqual(len(record["timing"]["raw_seconds"]), 9)
            self.assertIsNotNone(record["timing"]["median_seconds"])
            self.assertIsNotNone(record["timing"]["iqr_seconds"])
            self.assertIsNone(record["validation"]["passed"])
            self.assertIsNotNone(record["peak_python_allocation_bytes"])
            if sys.platform.startswith("linux"):
                self.assertIsNotNone(record["peak_rss_bytes"])
            self.assertEqual(list(output_dir.glob(".pending-*")), [])
            with self.assertRaises(ValueError):
                run_performance(output_dir=output_dir, profile="smoke",
                                benchmarks=("C01",), tasks=("C01:C",))

    def test_direct_solver_result_records_per_repetition_work(self):
        record = measure_task("C01", "A", profile="smoke", warmup=1,
                              repetitions=9)
        self.assertEqual(record["status"], "passed")
        self.assertEqual(len(record["work_samples"]), 9)
        self.assertEqual(record["work"], record["work_samples"][-1])
        self.assertGreater(record["work"]["rhs_evaluations"], 0)

    def test_task_filter_must_name_selected_registered_task(self):
        with TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "registered selected"):
            run_performance(output_dir=Path(directory), profile="smoke",
                            benchmarks=("C01",), tasks=("C02:main",))

    def test_fail_fast_and_continue_write_complete_manifests(self):
        failure = {"status": "failed", "error": "parity mismatch"}
        success = {"status": "passed", "error": None}
        with TemporaryDirectory() as directory:
            for fast, expected in ((True, 1), (False, 2)):
                with self.subTest(fail_fast=fast):
                    responses = [Mock(stdout=json.dumps(failure)),
                                 Mock(stdout=json.dumps(success))]
                    with patch("argesim_benchmarks.performance._git_sha",
                               return_value="a" * 40), \
                         patch("argesim_benchmarks.performance.subprocess.run",
                               side_effect=responses) as run:
                        path = Path(directory) / str(fast)
                        manifest = run_performance(
                            output_dir=path, profile="smoke",
                            benchmarks=("C01",), tasks=("C01:A", "C01:B"),
                            fail_fast=fast,
                        )
                    self.assertEqual(run.call_count, expected)
                    self.assertEqual(len(manifest["artifacts"]), expected)
                    self.assertEqual(manifest["failed"], 1)
                    self.assertEqual((path / "manifest.json").exists(), True)

    def test_timeout_writes_a_reproducible_failure_record(self):
        with TemporaryDirectory() as directory:
            with patch("argesim_benchmarks.performance._git_sha",
                       return_value="a" * 40), \
                 patch("argesim_benchmarks.performance.subprocess.run",
                       side_effect=subprocess.TimeoutExpired("worker", 0.1)):
                manifest = run_performance(
                    output_dir=Path(directory), profile="smoke",
                    benchmarks=("C01",), tasks=("C01:C",), timeout_s=0.1,
                )
            self.assertEqual((manifest["passed"], manifest["failed"]), (0, 1))
            record = json.loads((Path(directory) / "C01-C.json").read_text())
            self.assertIn("TimeoutExpired", record["error"])
            self.assertEqual(record["timeout_s"], 0.1)
            self.assertIn("effective_defaults", record["unavailable"])
            self.assertIsNone(record["validation"]["passed"])
            self.assertIsNone(record["timing"]["median_seconds"])


if __name__ == "__main__":
    unittest.main()
