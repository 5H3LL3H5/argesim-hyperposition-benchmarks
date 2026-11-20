"""Process-isolated boundary for a CIFASIS/qss-solver adapter.

The adapter is intentionally external: no CIFASIS source is copied, imported
or linked.  It must implement the versioned JSON protocol documented in
``docs/CIFASIS_ORACLE.md``.
"""

from __future__ import annotations

import json
import math
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from numbers import Real
from pathlib import Path
from typing import Any

from ..external import (
    AtomicArtifactDirectory,
    ExecutionEvidence,
    ExternalBackendProcess,
    canonical_json_bytes,
    environment_provenance,
    sha256_bytes,
)
from .base import OracleCapabilities, OracleResult, OracleStatus, SolverOracle

CIFASIS_PINNED_COMMIT = "4d53893958048273cb2dfd6fbd6e736f9dd0bbca"
ORACLE_PROTOCOL_VERSION = 1
_MAX_RESULT_BYTES = 16_777_216
_MAX_REQUEST_BYTES = 16_777_216
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_METHOD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.+-]{0,63}$")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is not permitted: {value}")


def _implementation_commit() -> str | None:
    configured = os.environ.get("ARGESIM_GIT_SHA")
    if configured:
        return configured if _COMMIT_RE.fullmatch(configured) else None
    try:
        root = Path(__file__).resolve().parents[2]
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if dirty.stdout:
            return None
        commit = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5.0,
        ).stdout.strip()
        return commit if _COMMIT_RE.fullmatch(commit) else None
    except (OSError, subprocess.SubprocessError):
        return None


class CifasisOracle(SolverOracle):
    """Safe subprocess facade for an external CIFASIS adapter."""

    def __init__(
        self,
        executable: Sequence[str] | None = None,
        *,
        expected_commit: str = CIFASIS_PINNED_COMMIT,
        probe_timeout_seconds: float = 10.0,
    ) -> None:
        if not _COMMIT_RE.fullmatch(expected_commit):
            raise ValueError("expected_commit must be a 40-character lowercase SHA")
        if (
            isinstance(probe_timeout_seconds, bool)
            or not isinstance(probe_timeout_seconds, Real)
            or not math.isfinite(probe_timeout_seconds)
            or probe_timeout_seconds <= 0.0
        ):
            raise ValueError("probe_timeout_seconds must be positive and finite")
        if executable is not None and (
            not executable
            or any(
                not isinstance(value, str) or not value or "\x00" in value
                for value in executable
            )
        ):
            raise ValueError(
                "executable argv must contain non-empty NUL-free strings"
            )
        self._configured = tuple(executable) if executable is not None else None
        self.expected_commit = expected_commit
        self.probe_timeout_seconds = probe_timeout_seconds
        self._process = ExternalBackendProcess()

    def _command(self) -> tuple[str, ...] | None:
        configured = self._configured
        if configured is None:
            from_environment = os.environ.get("ARGESIM_CIFASIS_ORACLE")
            if from_environment:
                configured = tuple(shlex.split(from_environment))
            else:
                resolved = shutil.which("argesim-cifasis-oracle")
                configured = (resolved,) if resolved else None
        if not configured or any(
            not isinstance(value, str) or not value or "\x00" in value
            for value in configured
        ):
            return None
        first = configured[0]
        if os.path.sep in first or (os.path.altsep and os.path.altsep in first):
            path = Path(first).expanduser()
            if not path.is_file() or not os.access(path, os.X_OK):
                return None
            resolved_first = str(path.resolve())
        else:
            resolved = shutil.which(first)
            if resolved is None:
                return None
            resolved_first = resolved
        return (resolved_first, *configured[1:])

    def capabilities(self) -> OracleCapabilities:
        command = self._command()
        if command is None:
            return OracleCapabilities(
                oracle="cifasis",
                status=OracleStatus.UNAVAILABLE,
                reason=(
                    "no CIFASIS oracle adapter was found; set "
                    "ARGESIM_CIFASIS_ORACLE or pass an executable argv"
                ),
            )
        with tempfile.TemporaryDirectory(prefix="argesim-cifasis-probe-") as name:
            try:
                observation = self._process.run(
                    (*command, "--argesim-oracle-probe", "--format", "json"),
                    cwd=Path(name),
                    timeout_seconds=self.probe_timeout_seconds,
                )
            except OSError as exc:
                return OracleCapabilities(
                    oracle="cifasis",
                    status=OracleStatus.UNAVAILABLE,
                    executable=command,
                    reason=f"adapter could not be started: {exc}",
                )
        if observation.timed_out:
            return OracleCapabilities(
                oracle="cifasis",
                status=OracleStatus.UNAVAILABLE,
                executable=command,
                reason="adapter capability probe timed out",
            )
        if observation.exit_code != 0:
            return OracleCapabilities(
                oracle="cifasis",
                status=OracleStatus.BUILD_REQUIRED,
                executable=command,
                reason=f"adapter probe exited with code {observation.exit_code}",
            )
        try:
            payload = json.loads(observation.stdout)
        except json.JSONDecodeError as exc:
            return OracleCapabilities(
                oracle="cifasis",
                status=OracleStatus.UNAVAILABLE,
                executable=command,
                reason=f"adapter probe returned invalid JSON: {exc}",
            )
        error = self._validate_capability_payload(payload)
        if error:
            return OracleCapabilities(
                oracle="cifasis",
                status=OracleStatus.UNAVAILABLE,
                executable=command,
                reason=error,
            )
        commit = payload["engine_commit"]
        if commit != self.expected_commit:
            return OracleCapabilities(
                oracle="cifasis",
                status=OracleStatus.BUILD_REQUIRED,
                executable=command,
                protocol_version=payload["protocol_version"],
                engine=payload["engine"],
                engine_commit=commit,
                methods=tuple(payload["methods"]),
                model_formats=tuple(payload["model_formats"]),
                reason=(
                    f"engine commit {commit} does not match pinned "
                    f"{self.expected_commit}"
                ),
            )
        return OracleCapabilities(
            oracle="cifasis",
            status=OracleStatus.AVAILABLE,
            executable=command,
            protocol_version=payload["protocol_version"],
            engine=payload["engine"],
            engine_commit=commit,
            methods=tuple(payload["methods"]),
            model_formats=tuple(payload["model_formats"]),
        )

    @staticmethod
    def _validate_capability_payload(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return "adapter probe result must be a JSON object"
        if payload.get("protocol_version") != ORACLE_PROTOCOL_VERSION:
            return "adapter protocol_version is missing or unsupported"
        if payload.get("engine") != "CIFASIS/qss-solver":
            return "adapter engine must be 'CIFASIS/qss-solver'"
        commit = payload.get("engine_commit")
        if not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit):
            return "adapter engine_commit must be a lowercase 40-character SHA"
        for field_name in ("methods", "model_formats"):
            values = payload.get(field_name)
            if not isinstance(values, list) or not values:
                return f"adapter {field_name} must be a non-empty JSON array"
            if any(
                not isinstance(value, str) or not _METHOD_RE.fullmatch(value)
                for value in values
            ):
                return f"adapter {field_name} contains an invalid identifier"
            if len({value.casefold() for value in values}) != len(values):
                return f"adapter {field_name} contains duplicates"
        return None

    def run(
        self,
        request: Mapping[str, Any],
        output_directory: Path,
        *,
        timeout_seconds: float = 300.0,
    ) -> OracleResult:
        if not isinstance(request, Mapping):
            raise TypeError("oracle request must be a JSON object")
        try:
            request_bytes = canonical_json_bytes(request)
        except ValueError as exc:
            raise ValueError(f"oracle request is not canonical JSON: {exc}") from exc
        if len(request_bytes) > _MAX_REQUEST_BYTES:
            raise ValueError("oracle request exceeds the 16 MiB limit")
        request_hash = sha256_bytes(request_bytes)
        if "model" not in request:
            raise ValueError("oracle request requires a model field")
        model_hash = sha256_bytes(canonical_json_bytes(request["model"]))
        method_value = request.get("method")
        method = method_value if isinstance(method_value, str) else None
        capabilities = self.capabilities()
        if not capabilities.available:
            return OracleResult(
                oracle="cifasis",
                status=capabilities.status,
                request_hash=request_hash,
                model_hash=model_hash,
                method=method,
                capabilities=capabilities,
                error=capabilities.reason,
                provenance=self._provenance(capabilities),
            )
        if method is None or not _METHOD_RE.fullmatch(method):
            return OracleResult(
                oracle="cifasis",
                status=OracleStatus.UNSUPPORTED_METHOD,
                request_hash=request_hash,
                model_hash=model_hash,
                method=method,
                capabilities=capabilities,
                error="request.method must be a valid method identifier",
                provenance=self._provenance(capabilities),
            )
        if method not in capabilities.methods:
            return OracleResult(
                oracle="cifasis",
                status=OracleStatus.UNSUPPORTED_METHOD,
                request_hash=request_hash,
                model_hash=model_hash,
                method=method,
                capabilities=capabilities,
                error=f"method {method!r} was not declared by the adapter",
                provenance=self._provenance(capabilities),
            )

        target = Path(output_directory)
        with AtomicArtifactDirectory(target) as bundle:
            assert bundle.path is not None
            temporary = bundle.path
            request_path = temporary / "request.json"
            request_path.write_bytes(request_bytes + b"\n")
            driver_result_path = temporary / "driver-result.json"
            command = capabilities.executable
            run_command = (
                *command,
                "--argesim-oracle-run",
                str(request_path),
                "--output",
                str(driver_result_path),
            )
            try:
                observation = self._process.run(
                    run_command,
                    cwd=temporary,
                    timeout_seconds=timeout_seconds,
                )
            except OSError as exc:
                observation = ExecutionEvidence(
                    argv=run_command,
                    exit_code=None,
                    duration_seconds=0.0,
                    timed_out=False,
                    stdout="",
                    stderr="",
                    stdout_truncated=False,
                    stderr_truncated=False,
                )
                error = f"adapter could not be started: {exc}"
                result_payload = None
            else:
                error, result_payload = self._read_driver_result(
                    observation, driver_result_path
                )
            status = (
                OracleStatus.SUCCEEDED
                if error is None
                else OracleStatus.EXECUTION_FAILED
            )
            result = OracleResult(
                oracle="cifasis",
                status=status,
                request_hash=request_hash,
                model_hash=model_hash,
                method=method,
                capabilities=capabilities,
                output_directory=str(target),
                duration_seconds=observation.duration_seconds,
                exit_code=observation.exit_code,
                timed_out=observation.timed_out,
                result=result_payload,
                error=error,
                provenance=self._provenance(capabilities),
            )
            self._write_bundle(temporary, observation, result)
            bundle.publish(scope=result.scope, status=result.status.value)
            return result

    @staticmethod
    def _read_driver_result(
        observation: ExecutionEvidence, result_path: Path
    ) -> tuple[str | None, Mapping[str, Any] | None]:
        if observation.timed_out:
            return "adapter execution timed out", None
        if observation.exit_code != 0:
            return f"adapter exited with code {observation.exit_code}", None
        if not result_path.is_file():
            return "adapter did not create driver-result.json", None
        try:
            if result_path.stat().st_size > _MAX_RESULT_BYTES:
                return "adapter result exceeds the 16 MiB limit", None
            payload = json.loads(
                result_path.read_text(encoding="utf-8"),
                parse_constant=_reject_json_constant,
            )
            canonical_json_bytes(payload)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            return f"adapter result is not valid JSON: {exc}", None
        if not isinstance(payload, dict):
            return "adapter result must be a JSON object", None
        return None, payload

    def _provenance(
        self, capabilities: OracleCapabilities
    ) -> dict[str, Any]:
        return {
            **environment_provenance(),
            "argesim_commit": _implementation_commit(),
            "cifasis_commit": capabilities.engine_commit,
            "cifasis_expected_commit": self.expected_commit,
        }

    @staticmethod
    def _write_bundle(
        directory: Path,
        observation: ExecutionEvidence,
        result: OracleResult,
    ) -> None:
        (directory / "stdout.txt").write_text(observation.stdout, encoding="utf-8")
        (directory / "stderr.txt").write_text(observation.stderr, encoding="utf-8")
        evidence = result.to_dict()
        evidence["process"] = {
            "argv": list(observation.argv),
            "stdout_truncated": observation.stdout_truncated,
            "stderr_truncated": observation.stderr_truncated,
        }
        (directory / "oracle-result.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
