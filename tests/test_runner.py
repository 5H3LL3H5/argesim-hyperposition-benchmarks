import json
import unittest
from contextlib import redirect_stdout
from io import StringIO

from argesim_benchmarks.cli import main
from argesim_benchmarks.runner import (
    BenchmarkTaskError,
    CONTRACTS,
    contract,
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


if __name__ == "__main__":
    unittest.main()
