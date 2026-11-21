import inspect
import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from argesim_benchmarks.cli import main
from argesim_benchmarks.runner import (
    CONTRACTS,
    BenchmarkTaskError,
    contract,
    run_suite,
    to_jsonable,
    verify_registry_complete,
)


class UnifiedRunnerTests(unittest.TestCase):
    def test_registry_covers_complete_active_catalog(self) -> None:
        verify_registry_complete()
        self.assertEqual(len(CONTRACTS), 24)

    def test_every_registered_entrypoint_resolves(self) -> None:
        for benchmark_contract in CONTRACTS.values():
            for task in benchmark_contract.tasks.values():
                self.assertTrue(callable(task.resolve()), task.entrypoint)

    def test_unknown_benchmark_and_task_are_strict(self) -> None:
        with self.assertRaises(BenchmarkTaskError):
            contract("C17")
        with self.assertRaises(BenchmarkTaskError):
            contract("C01").task("missing")
        with self.assertRaises(BenchmarkTaskError):
            contract("C01").run("A", {"unknown_argument": 1})

    def test_to_jsonable_handles_nested_reference_types(self) -> None:
        self.assertEqual(
            to_jsonable({"state": (1.0, 2.0), "flags": {2, 1}}),
            {"state": [1.0, 2.0], "flags": [1, 2]},
        )

    def test_cli_list_and_describe_are_machine_readable(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["list"]), 0)
        listing = json.loads(output.getvalue())
        self.assertEqual(len(listing), 24)

        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["describe", "CP2"]), 0)
        description = json.loads(output.getvalue())
        self.assertEqual(description["id"], "CP2")
        self.assertEqual(description["tasks"], ["1", "2", "3"])

    def test_cli_run_uses_same_task_contract(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["run", "C01", "C"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(set(result), {"bombardment", "no-bombardment"})
        self.assertEqual(len(result["bombardment"]), 3)

    def test_c17r_cli_accepts_a_json_intervention_object(self) -> None:
        for task, extra, event_field in (
            ("ode", {"t_bound": 2}, "events"),
            ("ca", {"steps": 2}, "interventions"),
        ):
            with self.subTest(task=task):
                kwargs = {"intervention": {"threshold_fraction": 0.04, "soft_factor": 0.5}}
                output = StringIO()
                with redirect_stdout(output):
                    self.assertEqual(
                        main(["run", "C17R", task, "--kwargs-json", json.dumps(kwargs | extra)]),
                        0,
                    )
                self.assertEqual(len(json.loads(output.getvalue())[event_field]), 1)

        with self.assertRaisesRegex(SystemExit, "invalid C17R intervention"):
            main([
                "run", "C17R", "ode", "--kwargs-json",
                '{"intervention":{"threshold":0.04,"soft_factor":0.5}}',
            ])

    def test_suite_covers_every_registered_task_and_records_required_inputs(self) -> None:
        import inspect

        from argesim_benchmarks.runner import _suite_arguments

        for profile in ("smoke", "definition"):
            arguments = _suite_arguments(profile)
            for identifier, benchmark_contract in CONTRACTS.items():
                for name, task in benchmark_contract.tasks.items():
                    with self.subTest(profile=profile, benchmark=identifier, task=name):
                        inspect.signature(task.resolve()).bind(**arguments.get((identifier, name), {}))

    def test_suite_reports_failure_and_continues_to_next_task(self) -> None:
        with patch.object(CONTRACTS["C01"], "run", side_effect=[ValueError("bad"), 5, 6]):
            report = run_suite(benchmarks=("C01",))
        self.assertEqual((report["passed"], report["failed"], report["total"]), (2, 1, 3))
        self.assertEqual(report["tasks"][0]["error"], "ValueError: bad")
        self.assertEqual(report["scope"], "execution only")

    def test_suite_evidence_preserves_failure_and_unavailable_measurements(self) -> None:
        with patch("argesim_benchmarks.runner._git_sha", return_value="a" * 40), \
             patch.object(CONTRACTS["C01"], "run", side_effect=[ValueError("bad"), 5, 6]):
            report = run_suite(benchmarks=("C01",))
        failed = report["tasks"][0]["evidence"]
        self.assertEqual(failed["schema_version"], 1)
        self.assertEqual(failed["scope"], "execution only")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["error"], "ValueError: bad")
        self.assertEqual(failed["experiment"]["implementation_git_sha"], "a" * 40)
        self.assertEqual(failed["experiment"]["benchmark"], "C01")
        self.assertEqual(failed["experiment"]["task"], "A")
        self.assertEqual(
            failed["experiment"]["timing"]["samples"],
            (failed["duration_seconds"],),
        )
        self.assertIsNone(failed["experiment"]["timing"]["iqr"])
        self.assertIsNone(failed["experiment"]["validation"]["passed"])
        self.assertIsNone(failed["experiment"]["work"]["rhs_evaluations"])
        self.assertIsNone(failed["peak_python_allocation_bytes"])
        self.assertIsNone(failed["peak_rss"])
        self.assertIn("validation", failed["unavailable"])
        self.assertEqual(report["tasks"][1]["evidence"]["status"], "passed")
        self.assertIsNone(report["tasks"][1]["evidence"]["error"])

    def test_suite_evidence_contains_effective_default_arguments(self) -> None:
        with patch.object(CONTRACTS["C01"], "run", return_value=5):
            report = run_suite(benchmarks=("C01",))
        row = report["tasks"][0]
        default = inspect.signature(CONTRACTS["C01"].task("A").resolve()).parameters[
            "t_bound"
        ].default
        self.assertEqual(
            row["evidence"]["experiment"]["input_parameters"]["t_bound"],
            default,
        )
        self.assertEqual(row["arguments"], {})

    def test_unresolvable_entrypoint_is_reported_without_stopping_suite(self) -> None:
        with patch.object(CONTRACTS["C01"].task("A"), "resolve", side_effect=ImportError("missing")), \
             patch.object(CONTRACTS["C01"], "run", return_value=5):
            report = run_suite(benchmarks=("C01",))
        self.assertEqual((report["passed"], report["failed"]), (2, 1))
        row = report["tasks"][0]
        self.assertEqual(row["error"], "ImportError: missing")
        self.assertIn("signature resolution failed", row["evidence"]["unavailable"]["effective_defaults"])

    def test_cli_suite_exit_code_and_json(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["run-suite", "--benchmark", "C01"]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["total"], 3)
        self.assertEqual(report["failed"], 0)

        with patch("argesim_benchmarks.cli.run_suite", return_value={
            "profile": "smoke", "scope": "execution only", "tasks": [],
            "passed": 0, "failed": 1, "total": 1,
        }), redirect_stdout(StringIO()):
            self.assertEqual(main(["run-suite", "--fail-fast"]), 1)


if __name__ == "__main__":
    unittest.main()
