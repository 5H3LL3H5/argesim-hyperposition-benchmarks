import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from argesim_benchmarks.cli import main
from argesim_benchmarks.runner import (
    BenchmarkTaskError,
    CONTRACTS,
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

    def test_suite_covers_every_registered_task_and_records_required_inputs(self) -> None:
        from argesim_benchmarks.runner import _suite_arguments
        import inspect

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
        }):
            with redirect_stdout(StringIO()):
                self.assertEqual(main(["run-suite", "--fail-fast"]), 1)


if __name__ == "__main__":
    unittest.main()
