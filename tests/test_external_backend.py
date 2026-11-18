import hashlib
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

from argesim_benchmarks.external import (
    AtomicArtifactDirectory,
    ExternalBackendProcess,
    canonical_json_bytes,
)


class ExternalBackendTests(unittest.TestCase):
    def test_runner_rejects_invalid_limits_timeout_and_cwd(self) -> None:
        for value in (True, -1, 1.5):
            with self.subTest(capture=value), self.assertRaises(ValueError):
                ExternalBackendProcess(max_capture_bytes=value)
        runner = ExternalBackendProcess()
        with tempfile.TemporaryDirectory() as name:
            cwd = Path(name)
            for timeout in (True, 0, -1, math.nan, math.inf):
                with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                    runner.run(
                        (sys.executable, "-c", "pass"),
                        cwd=cwd,
                        timeout_seconds=timeout,
                    )
            with self.assertRaisesRegex(ValueError, "existing directory"):
                runner.run(
                    (sys.executable, "-c", "pass"),
                    cwd=cwd / "missing",
                    timeout_seconds=1.0,
                )

    def test_runner_uses_argv_and_bounds_both_streams(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            observation = ExternalBackendProcess(max_capture_bytes=16).run(
                (
                    sys.executable,
                    "-c",
                    ("import sys; print(sys.argv[1]); "
                     "sys.stderr.write('x' * 40)"),
                    "; touch must-not-exist",
                ),
                cwd=Path(name),
                timeout_seconds=2.0,
            )
            self.assertEqual(observation.exit_code, 0)
            self.assertIn("; touch must", observation.stdout)
            self.assertTrue(observation.stderr_truncated)
            self.assertLessEqual(len(observation.stderr.encode()), 16)
            self.assertFalse((Path(name) / "must-not-exist").exists())

    def test_atomic_directory_hashes_and_preserves_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            target = Path(name) / "evidence"
            with AtomicArtifactDirectory(target) as bundle:
                assert bundle.path is not None
                (bundle.path / "result.json").write_bytes(b"{}\n")
                digests = bundle.publish(scope="diagnostic", status="ok")
            self.assertEqual(
                digests["result.json"], hashlib.sha256(b"{}\n").hexdigest()
            )
            manifest = json.loads((target / "manifest.json").read_text())
            self.assertEqual(manifest["artifacts"], digests)
            with self.assertRaises(FileExistsError), AtomicArtifactDirectory(target):
                pass

    def test_unpublished_directory_is_cleaned(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            target = Path(name) / "evidence"
            with self.assertRaisesRegex(RuntimeError, "stop"), AtomicArtifactDirectory(target) as bundle:
                assert bundle.path is not None
                staging = bundle.path
                raise RuntimeError("stop")
            self.assertFalse(staging.exists())
            self.assertFalse(target.exists())

    def test_artifact_bundle_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            target = root / "evidence"
            with self.assertRaisesRegex(ValueError, "symbolic link"), AtomicArtifactDirectory(target) as bundle:
                assert bundle.path is not None
                (bundle.path / "link").symlink_to(root / "outside")
                bundle.publish(scope="diagnostic", status="failed")
            self.assertFalse(target.exists())

    def test_canonical_json_is_order_independent_and_rejects_nan(self) -> None:
        self.assertEqual(
            canonical_json_bytes({"b": 1, "a": 2}),
            canonical_json_bytes({"a": 2, "b": 1}),
        )
        with self.assertRaises(ValueError):
            canonical_json_bytes({"value": float("nan")})


if __name__ == "__main__":
    unittest.main()
