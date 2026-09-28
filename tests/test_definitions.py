"""Checkpoint and scope contracts for grouped definition execution."""

import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from argesim_benchmarks.definitions import (
    DEFINITION_GROUPS, KNOWN_CONTRACT_GAPS, run_definition_group,
)
from argesim_benchmarks.runner import CONTRACTS, BenchmarkTaskError, run_suite


class DefinitionGroupTests(unittest.TestCase):
    def test_groups_partition_all_71_registered_tasks(self):
        identifiers = [name for group in DEFINITION_GROUPS.values() for name in group]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(set(identifiers), set(CONTRACTS))
        self.assertEqual(sum(len(CONTRACTS[name].tasks) for name in identifiers), 71)
        self.assertIn("CP2:3", KNOWN_CONTRACT_GAPS)

    def test_suite_task_filter_is_strict(self):
        with patch.object(CONTRACTS["C01"], "run", return_value=5):
            report = run_suite(benchmarks=("C01",), tasks=("C01:B",))
        self.assertEqual((report["passed"], report["total"]), (1, 1))
        self.assertEqual(report["tasks"][0]["task"], "B")
        with self.assertRaises(BenchmarkTaskError):
            run_suite(benchmarks=("C01",), tasks=("C02:main",))

    def test_checkpoint_resume_verifies_checksum_and_source(self):
        source = "a" * 40
        report = {"profile": "definition", "total": 1, "tasks": [{
            "benchmark": "C02", "task": "main", "status": "passed",
            "evidence": {"experiment": {"implementation_git_sha": source}},
        }]}
        response = Mock(stdout=json.dumps(report), stderr="", returncode=0)
        with TemporaryDirectory() as directory:
            with patch("argesim_benchmarks.definitions._git_sha",
                       return_value=source), \
                 patch("argesim_benchmarks.definitions.subprocess.run",
                       return_value=response) as worker:
                arguments = dict(group="C01-C06", output_dir=Path(directory),
                                 tasks=("C02:main",))
                manifest = run_definition_group(**arguments)
                self.assertEqual(worker.call_count, 1)
                self.assertEqual((manifest["completed"], manifest["passed"]), (1, 1))
                self.assertFalse(manifest["selection_covers_full_group"])
                self.assertFalse(manifest["registered_tasks_complete"])
                self.assertEqual(manifest["last_successful_task"], "C02:main")
                artifact = Path(directory) / "C01-C06" / "C02-main.json"
                row = json.loads(artifact.read_text())
                self.assertEqual(row["input_parameters"]["num_pallets"], 10)
                run_definition_group(**arguments, resume=True)
                self.assertEqual(worker.call_count, 1)
                artifact.write_text("corrupt")
                run_definition_group(**arguments, resume=True)
                self.assertEqual(worker.call_count, 2)
                with patch("argesim_benchmarks.definitions._git_sha",
                           return_value="b" * 40):
                    with self.assertRaisesRegex(ValueError, "manifest source"):
                        run_definition_group(**arguments, resume=True)

    def test_timeout_records_blocker_and_effective_inputs(self):
        with TemporaryDirectory() as directory:
            with patch("argesim_benchmarks.definitions._git_sha",
                       return_value="a" * 40), \
                 patch("argesim_benchmarks.definitions.subprocess.run",
                       side_effect=subprocess.TimeoutExpired("worker", 0.01)):
                manifest = run_definition_group(
                    group="C01-C06", output_dir=Path(directory),
                    tasks=("C02:main",), timeout_s=0.01,
                )
            self.assertEqual(manifest["blocked"], 1)
            self.assertIsNone(manifest["last_successful_task"])
            artifact = Path(directory) / "C01-C06" / "C02-main.json"
            record = json.loads(artifact.read_text())
            self.assertEqual(record["status"], "blocked")
            self.assertEqual(record["input_parameters"]["num_pallets"], 10)
            self.assertEqual(record["peak_rss_bytes"], None)
            self.assertIn("TimeoutExpired", record["error"])

    def test_interruption_before_first_task_can_resume(self):
        source = "a" * 40
        report = {"profile": "definition", "total": 1, "tasks": [{
            "benchmark": "C02", "task": "main", "status": "passed",
            "evidence": {"experiment": {"implementation_git_sha": source}},
        }]}
        with TemporaryDirectory() as directory:
            arguments = dict(group="C01-C06", output_dir=Path(directory),
                             tasks=("C02:main",))
            with patch("argesim_benchmarks.definitions._git_sha",
                       return_value=source):
                with patch("argesim_benchmarks.definitions.subprocess.run",
                           side_effect=KeyboardInterrupt), self.assertRaises(
                               KeyboardInterrupt
                           ):
                    run_definition_group(**arguments)
                manifest_path = Path(directory) / "C01-C06" / "manifest.json"
                self.assertEqual(json.loads(manifest_path.read_text())["completed"], 0)
                with patch("argesim_benchmarks.definitions.subprocess.run",
                           return_value=Mock(stdout=json.dumps(report), stderr="",
                                             returncode=0)):
                    resumed = run_definition_group(**arguments, resume=True)
                self.assertEqual(resumed["passed"], 1)


if __name__ == "__main__":
    unittest.main()
