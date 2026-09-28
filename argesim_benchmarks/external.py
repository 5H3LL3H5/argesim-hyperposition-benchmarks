"""Neutral infrastructure for optional process-isolated backends.

This module deliberately has no solver or oracle semantics.  A numerical
oracle, a learned surrogate, or another separately installed backend may use
the same execution and artifact primitives without sharing result types.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from numbers import Real
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ExecutionEvidence:
    """Bounded observation of one argv-based child process."""

    argv: tuple[str, ...]
    exit_code: int | None
    duration_seconds: float
    timed_out: bool
    stdout: str
    stderr: str
    stdout_truncated: bool
    stderr_truncated: bool
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically, rejecting NaN and unsupported types."""

    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"value is not canonical JSON: {exc}") from exc
    return text.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def environment_provenance() -> dict[str, str]:
    """Return a small secret-free description of the executing environment."""

    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
    }


class ExternalBackendProcess:
    """Execute a backend without a shell and bound captured output."""

    def __init__(self, *, max_capture_bytes: int = 1_048_576) -> None:
        if (
            isinstance(max_capture_bytes, bool)
            or not isinstance(max_capture_bytes, int)
            or max_capture_bytes < 0
        ):
            raise ValueError("max_capture_bytes must be a non-negative integer")
        self.max_capture_bytes = max_capture_bytes

    def _drain_stream(
        self,
        stream: Any,
        destination: bytearray,
        truncated: list[bool],
    ) -> None:
        while True:
            chunk = stream.read(65_536)
            if not chunk:
                break
            remaining = self.max_capture_bytes - len(destination)
            if remaining > 0:
                destination.extend(chunk[:remaining])
            if len(chunk) > remaining:
                truncated[0] = True

    @staticmethod
    def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                return
        else:  # pragma: no cover - exercised on Windows
            process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:  # pragma: no cover - exercised on Windows
                process.kill()
            process.wait()

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
    ) -> ExecutionEvidence:
        if not argv or any(
            not isinstance(value, str) or not value or "\x00" in value
            for value in argv
        ):
            raise ValueError("backend argv must contain non-empty NUL-free strings")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, Real)
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0.0
        ):
            raise ValueError("timeout_seconds must be positive and finite")
        if not Path(cwd).is_dir():
            raise ValueError("backend cwd must be an existing directory")

        creationflags = 0
        if os.name == "nt":  # pragma: no cover - exercised on Windows
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        started = time.monotonic()
        process = subprocess.Popen(
            list(argv),
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=os.name == "posix",
            creationflags=creationflags,
        )
        assert process.stdout is not None and process.stderr is not None
        stdout_bytes = bytearray()
        stderr_bytes = bytearray()
        stdout_truncated = [False]
        stderr_truncated = [False]
        threads = (
            threading.Thread(
                target=self._drain_stream,
                args=(process.stdout, stdout_bytes, stdout_truncated),
                daemon=True,
            ),
            threading.Thread(
                target=self._drain_stream,
                args=(process.stderr, stderr_bytes, stderr_truncated),
                daemon=True,
            ),
        )
        for thread in threads:
            thread.start()
        timed_out = False
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._terminate_process_group(process)
        for thread in threads:
            thread.join(timeout=2.0)
        process.stdout.close()
        process.stderr.close()
        return ExecutionEvidence(
            argv=tuple(argv),
            exit_code=process.returncode,
            duration_seconds=time.monotonic() - started,
            timed_out=timed_out,
            stdout=stdout_bytes.decode("utf-8", errors="replace"),
            stderr=stderr_bytes.decode("utf-8", errors="replace"),
            stdout_truncated=stdout_truncated[0],
            stderr_truncated=stderr_truncated[0],
        )


class AtomicArtifactDirectory:
    """Build a new evidence directory privately and publish it atomically."""

    def __init__(self, target: Path) -> None:
        self.target = Path(target).resolve()
        self.path: Path | None = None
        self._published = False

    def __enter__(self) -> "AtomicArtifactDirectory":
        parent = self.target.parent.resolve()
        parent.mkdir(parents=True, exist_ok=True)
        if self.target.exists():
            raise FileExistsError(f"artifact output already exists: {self.target}")
        self.path = Path(
            tempfile.mkdtemp(prefix=f".{self.target.name}.", dir=parent)
        )
        return self

    def publish(self, *, scope: str, status: str) -> Mapping[str, str]:
        if self.path is None or self._published:
            raise RuntimeError("artifact directory is not publishable")
        artifacts: dict[str, str] = {}
        for path in sorted(self.path.iterdir()):
            if path.is_symlink():
                raise ValueError(f"artifact must not be a symbolic link: {path.name}")
            if path.is_file() and path.name != "manifest.json":
                artifacts[path.name] = sha256_bytes(path.read_bytes())
            elif path.name != "manifest.json":
                raise ValueError(f"artifact must be a regular file: {path.name}")
        manifest = {
            "schema_version": 1,
            "scope": scope,
            "status": status,
            "artifacts": artifacts,
        }
        (self.path / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        os.replace(self.path, self.target)
        self._published = True
        return artifacts

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.path is not None and not self._published:
            shutil.rmtree(self.path, ignore_errors=True)
