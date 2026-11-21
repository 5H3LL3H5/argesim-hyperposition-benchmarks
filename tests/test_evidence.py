import json
import shutil
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from argesim_benchmarks import evidence
from argesim_benchmarks.evidence import (
    ExperimentRecord,
    RuntimeEnvironment,
    TimingEvidence,
    ValidationEvidence,
    WorkEvidence,
)


class EvidenceTests(unittest.TestCase):
    @patch("argesim_benchmarks.evidence.subprocess.run")
    def test_git_sha_is_resolved_from_package_repository(self, run) -> None:
        root = Path(evidence.__file__).resolve().parents[1]
        run.side_effect = [
            Mock(stdout=f"{root}\n"), Mock(stdout="# branch.oid abc123\n"),
            Mock(stdout=""),
        ]
        self.assertEqual(evidence._git_sha(), "abc123")
        command = run.call_args_list[0].args[0]
        self.assertEqual(command[:2], ("git", "-C"))
        self.assertEqual(command[-2:], ("rev-parse", "--show-toplevel"))
        self.assertEqual(run.call_args.args[0][-3:],
                         ("cat-file", "-e", "abc123:argesim_benchmarks/evidence.py"))

    @patch("argesim_benchmarks.evidence.subprocess.run")
    def test_dirty_checkout_has_no_implementation_sha(self, run) -> None:
        root = Path(evidence.__file__).resolve().parents[1]
        run.side_effect = [
            Mock(stdout=f"{root}\n"),
            Mock(stdout="# branch.oid abc123\n1 .M N... runner.py\n"),
        ]
        self.assertIsNone(evidence._git_sha())

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    @patch.dict("os.environ", {"ARGESIM_GIT_SHA": ""})
    def test_nested_or_ignored_install_never_claims_the_host_commit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / ".gitignore").write_text("deps/\nargesim_benchmarks/\n")

            def git(*args):
                return subprocess.check_output(
                    ["git", "-C", str(root), *args], text=True,
                ).strip()

            git("init", "-q")
            git("add", ".gitignore")
            git("-c", "user.name=Test fixture", "-c", "user.email=evidence@example.invalid",
                "commit", "-qm", "Host project")
            host_sha = git("rev-parse", "HEAD")
            for install_root in (root, root / "deps"):
                installed_source = install_root / "argesim_benchmarks" / "evidence.py"
                installed_source.parent.mkdir(parents=True)
                installed_source.write_text("# installed source\n")
                with self.subTest(install_root=install_root), patch.object(
                    evidence, "__file__", str(installed_source),
                ):
                    self.assertEqual(git("rev-parse", "HEAD"), host_sha)
                    self.assertIsNone(evidence._git_sha())

    def test_timing_summary_keeps_raw_samples(self) -> None:
        timing = TimingEvidence.from_samples((3.0, 1.0, 2.0), warmup=2)
        self.assertEqual(timing.samples, (3.0, 1.0, 2.0))
        self.assertEqual(timing.median, 2.0)
        self.assertEqual(timing.iqr, 1.0)
        self.assertEqual(timing.warmup, 2)
        self.assertEqual(timing.unit, "seconds")

    def test_timing_summary_rejects_invalid_input(self) -> None:
        with self.assertRaises(ValueError):
            TimingEvidence.from_samples((1.0,), warmup=-1)
        with self.assertRaises(ValueError):
            TimingEvidence.from_samples((-1.0,))
        with self.assertRaises(ValueError):
            TimingEvidence.from_samples((1.0,), unit="")
        with self.assertRaises(ValueError):
            TimingEvidence.from_samples((float("nan"),))
        with self.assertRaises(ValueError):
            TimingEvidence.from_samples((float("inf"),))

    def test_empty_timing_is_explicit(self) -> None:
        timing = TimingEvidence.from_samples(())
        self.assertIsNone(timing.median)
        self.assertIsNone(timing.iqr)

    def test_validation_and_work_reject_impossible_numbers(self) -> None:
        with self.assertRaises(ValueError):
            ValidationEvidence(error=float("nan"))
        with self.assertRaises(ValueError):
            ValidationEvidence(tolerance=-1.0)
        with self.assertRaises(ValueError):
            WorkEvidence(events=-1)

    @patch("argesim_benchmarks.evidence._git_sha", return_value="deadbeef")
    def test_record_is_machine_readable(self, _git) -> None:
        environment = RuntimeEnvironment(
            python="3.13.0",
            implementation="CPython",
            os="Linux",
            kernel="6.6.0",
            machine="x86_64",
            cpu_model="test-cpu",
            logical_cpus=8,
            cpu_affinity=(0, 1),
            cpu_governors=("performance",),
        )
        record = ExperimentRecord.capture(
            benchmark="CP2",
            benchmark_revision="CP2",
            task="task3",
            solver="bdf2",
            solver_parameters={"rtol": 1.0e-6},
            input_parameters={"unknowns": 499},
            seed=7,
            environment=environment,
            validation=ValidationEvidence(
                reference="fourier",
                metric="linf",
                error=2.0e-4,
                tolerance=5.0e-4,
                passed=True,
            ),
            work=WorkEvidence(accepted_steps=10, rejected_steps=1),
            timing=TimingEvidence.from_samples(
                (500.0, 400.0, 600.0), warmup=1, unit="milliseconds"
            ),
        )
        payload = json.loads(record.to_json())
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["implementation_git_sha"], "deadbeef")
        self.assertEqual(payload["benchmark"], "CP2")
        self.assertTrue(payload["captured_at_utc"].endswith("+00:00"))
        self.assertEqual(payload["environment"]["cpu_affinity"], [0, 1])
        self.assertEqual(payload["timing"]["samples"], [500.0, 400.0, 600.0])
        self.assertEqual(payload["timing"]["unit"], "milliseconds")
        self.assertTrue(payload["validation"]["passed"])


if __name__ == "__main__":
    unittest.main()
