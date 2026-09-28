import contextlib
import hashlib
import io
import json
import sys
import tempfile
import textwrap
import unittest
from argparse import ArgumentParser
from pathlib import Path
from unittest import mock

from argesim_benchmarks.oracles import (
    CIFASIS_PINNED_COMMIT,
    CifasisOracle,
    OracleStatus,
)
from argesim_benchmarks.oracles.cli import (
    add_oracle_commands,
    handle_oracle_command,
)


FAKE_DRIVER = r'''\
import argparse
import json
import os
import sys
import time

if "--argesim-oracle-probe" in sys.argv:
    print(json.dumps({
        "protocol_version": 1,
        "engine": "CIFASIS/qss-solver",
        "engine_commit": os.environ.get("FAKE_CIFASIS_COMMIT", "4d53893958048273cb2dfd6fbd6e736f9dd0bbca"),
        "methods": json.loads(os.environ.get("FAKE_METHODS", '["QSS1", "QSS2", "LIQSS2"]')),
        "model_formats": ["mu-modelica"],
    }))
    raise SystemExit(int(os.environ.get("FAKE_PROBE_EXIT", "0")))

parser = argparse.ArgumentParser()
parser.add_argument("--argesim-oracle-run", dest="request")
parser.add_argument("--output", required=True)
args = parser.parse_args()
if os.environ.get("FAKE_SLEEP"):
    time.sleep(float(os.environ["FAKE_SLEEP"]))
request = json.loads(open(args.request, encoding="utf-8").read())
with open(args.output, "w", encoding="utf-8") as stream:
    if os.environ.get("FAKE_RESULT_NAN"):
        stream.write('{"value": NaN}')
    else:
        json.dump({"method": request["method"], "trajectory": [[0.0, 1.0]]}, stream)
print("fake-driver-ok")
raise SystemExit(int(os.environ.get("FAKE_RUN_EXIT", "0")))
'''


class CifasisOracleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.driver = self.root / "fake_driver.py"
        self.driver.write_text(textwrap.dedent(FAKE_DRIVER), encoding="utf-8")
        self.oracle = CifasisOracle((sys.executable, str(self.driver)))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_missing_adapter_is_structured_unavailable(self) -> None:
        oracle = CifasisOracle((str(self.root / "missing"),))
        capabilities = oracle.capabilities()
        self.assertEqual(capabilities.status, OracleStatus.UNAVAILABLE)
        self.assertFalse(capabilities.available)
        self.assertIn("no CIFASIS oracle adapter", capabilities.reason)

    def test_constructor_rejects_invalid_argv_and_probe_timeout(self) -> None:
        for argv in ((), ("",), ("tool", ""), ("tool", "bad\x00arg")):
            with self.subTest(argv=argv), self.assertRaises(ValueError):
                CifasisOracle(argv)
        for timeout in (True, 0, -1, float("nan"), float("inf")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                CifasisOracle((sys.executable,), probe_timeout_seconds=timeout)

    def test_probe_requires_pinned_commit(self) -> None:
        with mock.patch.dict(
            "os.environ", {"FAKE_CIFASIS_COMMIT": "a" * 40}
        ):
            capabilities = self.oracle.capabilities()
        self.assertEqual(capabilities.status, OracleStatus.BUILD_REQUIRED)
        self.assertEqual(capabilities.engine_commit, "a" * 40)
        self.assertIn(CIFASIS_PINNED_COMMIT, capabilities.reason)

    def test_probe_rejects_case_insensitive_duplicate_methods(self) -> None:
        with mock.patch.dict(
            "os.environ", {"FAKE_METHODS": '["QSS2", "qss2"]'}
        ):
            capabilities = self.oracle.capabilities()
        self.assertEqual(capabilities.status, OracleStatus.UNAVAILABLE)
        self.assertIn("duplicates", capabilities.reason)

    def test_success_publishes_atomic_hashed_artifacts(self) -> None:
        target = self.root / "evidence"
        result = self.oracle.run(
            {"model": {"name": "decay", "rate": 1.0}, "method": "QSS2"},
            target,
        )
        self.assertTrue(result.succeeded)
        self.assertEqual(result.status, OracleStatus.SUCCEEDED)
        self.assertEqual(result.result["method"], "QSS2")
        manifest = json.loads((target / "manifest.json").read_text())
        self.assertEqual(manifest["scope"], "external execution observation only")
        self.assertNotIn("manifest.json", manifest["artifacts"])
        for name, digest in manifest["artifacts"].items():
            self.assertEqual(
                hashlib.sha256((target / name).read_bytes()).hexdigest(), digest
            )
        evidence = json.loads((target / "oracle-result.json").read_text())
        self.assertEqual(evidence["provenance"]["cifasis_commit"], CIFASIS_PINNED_COMMIT)
        self.assertEqual(evidence["model_hash"], result.model_hash)
        self.assertEqual((target / "stdout.txt").read_text(), "fake-driver-ok\n")

    def test_unsupported_method_never_starts_run_or_creates_directory(self) -> None:
        target = self.root / "unsupported"
        result = self.oracle.run({"model": "decay", "method": "CQSS3"}, target)
        self.assertEqual(result.status, OracleStatus.UNSUPPORTED_METHOD)
        self.assertFalse(target.exists())
        case_mismatch = self.oracle.run(
            {"model": "decay", "method": "qss2"}, self.root / "case-mismatch"
        )
        self.assertEqual(case_mismatch.status, OracleStatus.UNSUPPORTED_METHOD)

    def test_timeout_is_failure_and_still_publishes_diagnostics(self) -> None:
        target = self.root / "timeout"
        with mock.patch.dict("os.environ", {"FAKE_SLEEP": "2"}):
            result = self.oracle.run(
                {"model": "decay", "method": "QSS1"},
                target,
                timeout_seconds=0.05,
            )
        self.assertEqual(result.status, OracleStatus.EXECUTION_FAILED)
        self.assertTrue(result.timed_out)
        self.assertTrue(target.is_dir())
        self.assertEqual(
            json.loads((target / "manifest.json").read_text())["status"],
            "execution-failed",
        )

    def test_non_finite_driver_json_is_a_published_execution_failure(self) -> None:
        target = self.root / "nan-result"
        with mock.patch.dict("os.environ", {"FAKE_RESULT_NAN": "1"}):
            result = self.oracle.run(
                {"model": "decay", "method": "QSS1"}, target
            )
        self.assertEqual(result.status, OracleStatus.EXECUTION_FAILED)
        self.assertIn("not valid JSON", result.error)
        self.assertTrue(target.is_dir())
        evidence = json.loads((target / "oracle-result.json").read_text())
        self.assertEqual(evidence["status"], "execution-failed")

    def test_existing_output_is_never_overwritten(self) -> None:
        target = self.root / "existing"
        target.mkdir()
        sentinel = target / "sentinel"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            self.oracle.run({"model": "decay", "method": "QSS1"}, target)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_request_rejects_non_finite_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "canonical JSON"):
            self.oracle.run(
                {"model": "decay", "method": "QSS1", "value": float("nan")},
                self.root / "nan",
            )

    def test_cli_probe_and_run_are_machine_readable(self) -> None:
        parser = ArgumentParser()
        commands = parser.add_subparsers(dest="command", required=True)
        add_oracle_commands(commands)
        probe = parser.parse_args(
            ["oracle", "probe", "cifasis", "--executable", sys.executable,
             "--adapter-arg", str(self.driver)]
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(handle_oracle_command(probe), 0)
        self.assertTrue(json.loads(output.getvalue())["available"])

        request = self.root / "request-input.json"
        request.write_text(
            json.dumps({"model": "decay", "method": "LIQSS2"}),
            encoding="utf-8",
        )
        run = parser.parse_args(
            [
                "oracle", "run", "cifasis", "--executable", sys.executable,
                "--adapter-arg", str(self.driver), "--request", str(request),
                "--output-dir", str(self.root / "cli-output"),
            ]
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(handle_oracle_command(run), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "succeeded")


if __name__ == "__main__":
    unittest.main()
