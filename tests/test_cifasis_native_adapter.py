import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

from argesim_benchmarks.oracles import CifasisOracle, OracleStatus
from argesim_benchmarks.oracles.cifasis_adapter import main


COMPILE_DRIVER = r'''#!/usr/bin/env python3
import os
import pathlib
import sys

if "ARGESIM_TEST_SECRET" in os.environ:
    print("parent secret leaked", file=sys.stderr)
    raise SystemExit(9)
required_environment = {
    "MMOC_PATH",
    "MMOC_SRC",
    "MMOC_DOC",
    "MMOC_LIBS",
    "MMOC_BIN",
    "MMOC_MODELS",
    "MMOC_BUILD",
    "MMOC_OUTPUT",
    "MMOC_LOG",
    "MMOC_PACKAGES",
    "MMOC_LIBRARIES",
    "MMOC_TESTS",
    "MMOC_ENGINE",
    "MMOC_INCLUDE",
}
missing = sorted(required_environment - os.environ.keys())
if missing:
    print(f"missing CIFASIS environment: {missing}", file=sys.stderr)
    raise SystemExit(10)
model = sys.argv[1]
source = pathlib.Path(sys.argv[2]) / f"{model}.mo"
if not source.is_file():
    print("model source missing", file=sys.stderr)
    raise SystemExit(8)
build = pathlib.Path(os.environ["MMOC_BUILD"]) / model
build.mkdir(parents=True)
(build / model).write_text("fake executable", encoding="utf-8")
print("fake compile ok")
'''


SIMULATE_DRIVER = r'''#!/usr/bin/env python3
import os
import pathlib
import sys

model = sys.argv[1]
output = pathlib.Path(os.environ["MMOC_OUTPUT"]) / model
output.mkdir(parents=True)
(output / "x.dat").write_text(
    "0 1\n0.5 0.6065306597\n1 0.3678794412\n", encoding="utf-8"
)
print("fake simulation ok")
'''


class CifasisNativeAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "qss-source"
        self.install = self.root / "qss-install"
        self.source.mkdir()
        (self.install / "bin").mkdir(parents=True)
        (self.source / "README").write_text("fake qss source\n", encoding="utf-8")
        source_khmetis = (
            self.source
            / "src"
            / "engine"
            / "3rd-party"
            / "partitioners"
            / "hmetis"
            / "khmetis"
        )
        source_khmetis.parent.mkdir(parents=True)
        source_khmetis.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        source_khmetis.chmod(0o755)
        subprocess.run(
            ["git", "init", "-q"], cwd=self.source, check=True
        )
        subprocess.run(["git", "add", "."], cwd=self.source, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=ARGESIM Test",
                "-c",
                "user.email=argesim@example.invalid",
                "commit",
                "-q",
                "-m",
                "test fixture",
            ],
            cwd=self.source,
            check=True,
        )
        self.commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.source,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self._write_executable("mmoc", "#!/bin/sh\nexit 0\n")
        self._write_executable("khmetis", "#!/bin/sh\nexit 0\n")
        self._write_executable("compile.sh", COMPILE_DRIVER)
        self._write_executable("simulate.sh", SIMULATE_DRIVER)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_executable(self, name: str, content: str) -> Path:
        path = self.install / "bin" / name
        path.write_text(textwrap.dedent(content), encoding="utf-8")
        path.chmod(0o755)
        return path

    def _arguments(self) -> list[str]:
        return [
            "--source-root",
            str(self.source),
            "--install-root",
            str(self.install),
        ]

    @staticmethod
    def _request() -> dict[str, object]:
        return {
            "schema_version": 1,
            "model": {
                "type": "scalar-linear-decay",
                "rate": 1.0,
                "initial_value": 1.0,
            },
            "method": "QSS2",
            "simulation": {
                "start_time": 0.0,
                "stop_time": 1.0,
                "relative_tolerance": 1e-4,
                "absolute_tolerance": 1e-7,
            },
            "outputs": ["x"],
        }

    def _run_main(
        self,
        request: dict[str, object] | None = None,
        *,
        output_name: str = "result.json",
    ) -> tuple[int, Path, str]:
        request_path = self.root / "request.json"
        request_path.write_text(
            json.dumps(request or self._request()), encoding="utf-8"
        )
        output = self.root / output_name
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main(
                [
                    *self._arguments(),
                    "--argesim-oracle-run",
                    str(request_path),
                    "--output",
                    str(output),
                ]
            )
        return result, output, stderr.getvalue()

    def test_probe_reports_observed_clean_commit_and_pilot_methods(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = main([*self._arguments(), "--argesim-oracle-probe"])
        self.assertEqual(result, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["engine_commit"], self.commit)
        self.assertEqual(payload["methods"], ["QSS1", "QSS2"])
        self.assertEqual(payload["model_formats"], ["mu-modelica"])

    def test_probe_rejects_dirty_source_and_missing_installation(self) -> None:
        (self.source / "untracked").write_text("dirty", encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main([*self._arguments(), "--argesim-oracle-probe"])
        self.assertEqual(result, 2)
        self.assertIn("checkout is dirty", stderr.getvalue())
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main(
                [
                    "--source-root",
                    str(self.source),
                    "--install-root",
                    str(self.root / "missing"),
                    "--argesim-oracle-probe",
                ]
            )
        self.assertEqual(result, 2)
        self.assertIn("not a directory", stderr.getvalue())

    def test_probe_accepts_upstream_khmetis_location(self) -> None:
        (self.install / "bin" / "khmetis").unlink()
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = main([*self._arguments(), "--argesim-oracle-probe"])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue())["engine_commit"], self.commit)

    def test_native_run_normalizes_trajectory_and_records_model(self) -> None:
        result, output, stderr = self._run_main()
        self.assertEqual((result, stderr), (0, ""))
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["engine_commit"], self.commit)
        self.assertEqual(payload["method"], "QSS2")
        self.assertEqual(payload["native_method"], "QSS2")
        self.assertEqual(payload["trajectory"]["x"]["time"], [0.0, 0.5, 1.0])
        self.assertEqual(payload["metrics"]["output_samples"], 3)
        self.assertTrue(
            payload["validation"]["sampled_points_within_requested_tolerance"]
        )
        self.assertTrue(payload["validation"]["terminal_sample_present"])
        self.assertLess(payload["validation"]["max_scaled_error"], 1.0)
        self.assertIn("MMO_Solver=QSS2", payload["model"]["source"])
        self.assertIn("der(x) = -rate * x", payload["model"]["source"])
        self.assertEqual(payload["scope"], "external execution observation only")

    def test_native_children_do_not_receive_unlisted_parent_environment(self) -> None:
        with mock.patch.dict(os.environ, {"ARGESIM_TEST_SECRET": "do-not-forward"}):
            result, output, stderr = self._run_main(output_name="sanitized.json")
        self.assertEqual((result, stderr), (0, ""))
        self.assertTrue(output.is_file())

    def test_oracle_boundary_executes_native_adapter_end_to_end(self) -> None:
        executable = (
            sys.executable,
            "-m",
            "argesim_benchmarks.oracles.cifasis_adapter",
            *self._arguments(),
        )
        oracle = CifasisOracle(executable, expected_commit=self.commit)
        package_root = str(Path(__file__).resolve().parents[1])
        inherited_path = os.environ.get("PYTHONPATH")
        python_path = os.pathsep.join(
            [package_root] + ([inherited_path] if inherited_path else [])
        )
        with mock.patch.dict(os.environ, {"PYTHONPATH": python_path}):
            capabilities = oracle.capabilities()
            self.assertTrue(capabilities.available, capabilities.reason)
            output = self.root / "evidence"
            result = oracle.run(self._request(), output)
        self.assertEqual(result.status, OracleStatus.SUCCEEDED)
        self.assertEqual(result.result["native_method"], "QSS2")
        self.assertTrue((output / "manifest.json").is_file())

    def test_request_rejects_arbitrary_model_and_unknown_fields(self) -> None:
        request = self._request()
        request["model"] = {"type": "raw-modelica", "source": "dangerous()"}
        result, output, stderr = self._run_main(request)
        self.assertEqual(result, 2)
        self.assertFalse(output.exists())
        self.assertIn("unsupported model fields", stderr)
        request = self._request()
        request["shell_flags"] = "$(arbitrary)"
        result, output, stderr = self._run_main(request, output_name="unknown.json")
        self.assertEqual(result, 2)
        self.assertFalse(output.exists())
        self.assertIn("unsupported request fields", stderr)
        request = self._request()
        request["model"]["rate"] = -1.0
        result, output, stderr = self._run_main(request, output_name="rate.json")
        self.assertEqual(result, 2)
        self.assertFalse(output.exists())
        self.assertIn("greater than zero", stderr)

    def test_failed_compile_and_invalid_trajectory_do_not_publish_result(self) -> None:
        self._write_executable(
            "compile.sh",
            "#!/bin/sh\necho controlled compiler failure >&2\nexit 7\n",
        )
        result, output, stderr = self._run_main(output_name="compile-fail.json")
        self.assertEqual(result, 2)
        self.assertFalse(output.exists())
        self.assertIn("exited with code 7", stderr)
        self._write_executable("compile.sh", COMPILE_DRIVER)
        self._write_executable(
            "simulate.sh",
            r'''#!/usr/bin/env python3
import os
import pathlib
import sys
output = pathlib.Path(os.environ["MMOC_OUTPUT"]) / sys.argv[1]
output.mkdir(parents=True)
(output / "x.dat").write_text("1 1\n0 2\n", encoding="utf-8")
''',
        )
        result, output, stderr = self._run_main(output_name="bad-time.json")
        self.assertEqual(result, 2)
        self.assertFalse(output.exists())
        self.assertIn("time decreases", stderr)
        self._write_executable(
            "simulate.sh",
            r'''#!/usr/bin/env python3
import os
import pathlib
import sys
output = pathlib.Path(os.environ["MMOC_OUTPUT"]) / sys.argv[1]
output.mkdir(parents=True)
(output / "x.dat").write_text("0 1\n", encoding="utf-8")
(output / "unexpected.dat").write_text("0 1\n", encoding="utf-8")
''',
        )
        result, output, stderr = self._run_main(output_name="two.json")
        self.assertEqual(result, 2)
        self.assertFalse(output.exists())
        self.assertIn("exactly one", stderr)

    def test_existing_result_is_never_overwritten(self) -> None:
        output = self.root / "existing.json"
        output.write_text("sentinel", encoding="utf-8")
        result, returned, stderr = self._run_main(output_name="existing.json")
        self.assertEqual(result, 2)
        self.assertEqual(returned.read_text(encoding="utf-8"), "sentinel")
        self.assertIn("already exists", stderr)


if __name__ == "__main__":
    unittest.main()
