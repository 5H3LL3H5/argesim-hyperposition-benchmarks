"""Native process adapter for a pinned CIFASIS/qss-solver installation.

This is deliberately a narrow first integration: it translates one analytic
linear-decay pilot model to deterministic micro-Modelica and exposes QSS1 and
QSS2 only.  Additional models and methods require separate qualification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..external import canonical_json_bytes
from .cifasis import ORACLE_PROTOCOL_VERSION

_MAX_REQUEST_BYTES = 16_777_216
_MAX_OUTPUT_BYTES = 16_777_216
_MAX_DIAGNOSTIC_BYTES = 1_048_576
_METHODS = {"QSS1": "QSS", "QSS2": "QSS2"}
_MODEL_TYPE = "scalar-linear-decay"
_MODEL_NAME = "argesim_linear_decay"


class AdapterError(RuntimeError):
    """Controlled adapter failure suitable for a concise stderr diagnostic."""


@dataclass(frozen=True)
class Installation:
    source_root: Path
    install_root: Path
    commit: str
    mmoc: Path
    compile_script: Path
    simulate_script: Path


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdapterError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise AdapterError(f"{field} must be a finite number")
    return result


def _positive_number(value: Any, field: str) -> float:
    result = _finite_number(value, field)
    if result <= 0.0:
        raise AdapterError(f"{field} must be greater than zero")
    return result


def _bounded_text(data: bytes) -> tuple[str, bool]:
    truncated = len(data) > _MAX_DIAGNOSTIC_BYTES
    return data[:_MAX_DIAGNOSTIC_BYTES].decode("utf-8", errors="replace"), truncated


def _run_checked(
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
) -> tuple[float, str, str, bool, bool]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(argv),
            cwd=cwd,
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            shell=False,
            check=False,
        )
    except OSError as exc:
        raise AdapterError(f"could not start {Path(argv[0]).name}: {exc}") from exc
    duration = time.monotonic() - started
    stdout, stdout_truncated = _bounded_text(completed.stdout)
    stderr, stderr_truncated = _bounded_text(completed.stderr)
    if completed.returncode != 0:
        detail = stderr.strip() or stdout.strip() or "no diagnostic output"
        raise AdapterError(
            f"{Path(argv[0]).name} exited with code {completed.returncode}: {detail}"
        )
    return duration, stdout, stderr, stdout_truncated, stderr_truncated


def _git_commit(source_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "--verify", "HEAD"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            shell=False,
            check=False,
            timeout=5.0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AdapterError(f"cannot inspect CIFASIS source revision: {exc}") from exc
    commit = completed.stdout.decode("ascii", errors="ignore").strip()
    if completed.returncode != 0 or len(commit) != 40 or any(
        character not in "0123456789abcdef" for character in commit
    ):
        raise AdapterError("CIFASIS source root is not a readable Git checkout")
    try:
        status = subprocess.run(
            [
                "git",
                "-C",
                str(source_root),
                "status",
                "--porcelain",
                "--untracked-files=normal",
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            shell=False,
            check=False,
            timeout=5.0,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AdapterError(f"cannot inspect CIFASIS source status: {exc}") from exc
    if status.returncode != 0:
        raise AdapterError("cannot inspect CIFASIS source status")
    if status.stdout.strip():
        raise AdapterError("CIFASIS source checkout is dirty")
    return commit


def _resolve_installation(
    source_value: str | None,
    install_value: str | None,
) -> Installation:
    source_text = source_value or os.environ.get("ARGESIM_CIFASIS_SOURCE")
    install_text = install_value or os.environ.get("ARGESIM_CIFASIS_ROOT")
    if not source_text:
        raise AdapterError(
            "CIFASIS source is not configured; set ARGESIM_CIFASIS_SOURCE"
        )
    if not install_text:
        raise AdapterError(
            "CIFASIS installation is not configured; set ARGESIM_CIFASIS_ROOT"
        )
    source_root = Path(source_text).expanduser().resolve()
    install_root = Path(install_text).expanduser().resolve()
    if not source_root.is_dir():
        raise AdapterError(f"CIFASIS source root is not a directory: {source_root}")
    if not install_root.is_dir():
        raise AdapterError(
            f"CIFASIS installation root is not a directory: {install_root}"
        )
    bin_directory = install_root / "bin"
    required = {
        "mmoc": bin_directory / "mmoc",
        "compile.sh": bin_directory / "compile.sh",
        "simulate.sh": bin_directory / "simulate.sh",
        "khmetis": bin_directory / "khmetis",
    }
    for label, path in required.items():
        if not path.is_file() or not os.access(path, os.X_OK):
            raise AdapterError(f"required CIFASIS executable is unavailable: {label}")
    return Installation(
        source_root=source_root,
        install_root=install_root,
        commit=_git_commit(source_root),
        mmoc=required["mmoc"],
        compile_script=required["compile.sh"],
        simulate_script=required["simulate.sh"],
    )


def _load_request(path: Path) -> Mapping[str, Any]:
    try:
        if path.is_symlink() or not path.is_file():
            raise AdapterError("request path is not a regular file")
        if path.stat().st_size > _MAX_REQUEST_BYTES:
            raise AdapterError("request exceeds the 16 MiB limit")
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant: {value}")
            ),
        )
        canonical_json_bytes(payload)
    except AdapterError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise AdapterError(f"request is not valid finite JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise AdapterError("request must be a JSON object")
    return payload


def _validated_request(request: Mapping[str, Any]) -> dict[str, Any]:
    allowed_top = {"schema_version", "model", "method", "simulation", "outputs"}
    unknown_top = sorted(set(request) - allowed_top)
    if unknown_top:
        raise AdapterError(f"unsupported request fields: {', '.join(unknown_top)}")
    if request.get("schema_version", 1) != 1:
        raise AdapterError("request schema_version must be 1")
    method = request.get("method")
    if method not in _METHODS:
        raise AdapterError("pilot adapter supports only QSS1 and QSS2")
    model = request.get("model")
    if not isinstance(model, dict):
        raise AdapterError("request.model must be a JSON object")
    allowed_model = {"type", "rate", "initial_value"}
    unknown_model = sorted(set(model) - allowed_model)
    if unknown_model:
        raise AdapterError(f"unsupported model fields: {', '.join(unknown_model)}")
    if model.get("type") != _MODEL_TYPE:
        raise AdapterError(f"pilot adapter requires model.type={_MODEL_TYPE!r}")
    rate = _positive_number(model.get("rate"), "model.rate")
    initial_value = _finite_number(
        model.get("initial_value"), "model.initial_value"
    )
    simulation = request.get("simulation")
    if not isinstance(simulation, dict):
        raise AdapterError("request.simulation must be a JSON object")
    allowed_simulation = {
        "start_time",
        "stop_time",
        "relative_tolerance",
        "absolute_tolerance",
    }
    unknown_simulation = sorted(set(simulation) - allowed_simulation)
    if unknown_simulation:
        raise AdapterError(
            f"unsupported simulation fields: {', '.join(unknown_simulation)}"
        )
    start_time = _finite_number(
        simulation.get("start_time", 0.0), "simulation.start_time"
    )
    stop_time = _finite_number(
        simulation.get("stop_time"), "simulation.stop_time"
    )
    if stop_time <= start_time:
        raise AdapterError("simulation.stop_time must be greater than start_time")
    relative_tolerance = _positive_number(
        simulation.get("relative_tolerance"), "simulation.relative_tolerance"
    )
    absolute_tolerance = _positive_number(
        simulation.get("absolute_tolerance"), "simulation.absolute_tolerance"
    )
    outputs = request.get("outputs", ["x"])
    if outputs != ["x"]:
        raise AdapterError("pilot adapter supports exactly outputs=['x']")
    return {
        "method": method,
        "solver": _METHODS[method],
        "rate": rate,
        "initial_value": initial_value,
        "start_time": start_time,
        "stop_time": stop_time,
        "relative_tolerance": relative_tolerance,
        "absolute_tolerance": absolute_tolerance,
    }


def _number(value: float) -> str:
    return format(value, ".17g")


def _model_source(configuration: Mapping[str, Any]) -> str:
    return (
        f"model {_MODEL_NAME}\n"
        "  Real x;\n"
        f"  parameter Real rate = {_number(configuration['rate'])};\n"
        "  initial algorithm\n"
        f"    x := {_number(configuration['initial_value'])};\n"
        "  equation\n"
        "    der(x) = -rate * x;\n"
        "  annotation(\n"
        "    experiment(\n"
        '      MMO_Description="ARGESIM analytic linear-decay pilot",\n'
        f"      MMO_Solver={configuration['solver']},\n"
        "      MMO_PartitionMethod=Metis,\n"
        "      MMO_Output={x},\n"
        "      Jacobian=Dense,\n"
        f"      StartTime={_number(configuration['start_time'])},\n"
        f"      StopTime={_number(configuration['stop_time'])},\n"
        f"      Tolerance={{{_number(configuration['relative_tolerance'])}}},\n"
        f"      AbsTolerance={{{_number(configuration['absolute_tolerance'])}}}\n"
        "    )\n"
        "  );\n"
        f"end {_MODEL_NAME};\n"
    )


def _read_trajectory(output_directory: Path) -> tuple[list[float], list[float], str]:
    candidates = sorted(output_directory.glob("*.dat"))
    if len(candidates) != 1:
        raise AdapterError(
            f"expected exactly one CIFASIS .dat output, found {len(candidates)}"
        )
    path = candidates[0]
    if path.is_symlink() or not path.is_file():
        raise AdapterError("CIFASIS output is not a regular file")
    if path.stat().st_size > _MAX_OUTPUT_BYTES:
        raise AdapterError("CIFASIS trajectory exceeds the 16 MiB limit")
    times: list[float] = []
    values: list[float] = []
    try:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            columns = stripped.replace(",", " ").split()
            if len(columns) != 2:
                raise AdapterError(
                    f"invalid trajectory row {line_number}: expected two columns"
                )
            time_value, state_value = (float(column) for column in columns)
            if not math.isfinite(time_value) or not math.isfinite(state_value):
                raise AdapterError(
                    f"non-finite trajectory value at row {line_number}"
                )
            if times and time_value < times[-1]:
                raise AdapterError(
                    f"trajectory time decreases at row {line_number}"
                )
            times.append(time_value)
            values.append(state_value)
    except UnicodeError as exc:
        raise AdapterError(f"trajectory is not UTF-8: {exc}") from exc
    except ValueError as exc:
        raise AdapterError(f"trajectory contains a non-numeric value: {exc}") from exc
    if not times:
        raise AdapterError("CIFASIS trajectory is empty")
    return times, values, path.name


def _environment(installation: Installation, workspace: Path) -> dict[str, str]:
    inherited_names = (
        "PATH",
        "HOME",
        "TMPDIR",
        "TMP",
        "TEMP",
        "SYSTEMROOT",
        "COMSPEC",
        "PATHEXT",
    )
    environment = {
        name: os.environ[name] for name in inherited_names if name in os.environ
    }
    bin_directory = installation.install_root / "bin"
    library_candidates = (
        installation.install_root / "lib",
        bin_directory / "lib",
    )
    existing_library_path = environment.get("LD_LIBRARY_PATH", "")
    library_path = os.pathsep.join(
        [str(path) for path in library_candidates if path.is_dir()]
        + ([existing_library_path] if existing_library_path else [])
    )
    environment.update(
        {
            "MMOC_BIN": str(bin_directory),
            "MMOC_MODELS": str(workspace / "models"),
            "MMOC_BUILD": str(workspace / "build"),
            "MMOC_OUTPUT": str(workspace / "output"),
            "MMOC_LOG": str(workspace / "log"),
            "LC_ALL": "C",
            "LANG": "C",
        }
    )
    if library_path:
        environment["LD_LIBRARY_PATH"] = library_path
    return environment


def _execute(
    installation: Installation,
    request: Mapping[str, Any],
    base_directory: Path,
) -> dict[str, Any]:
    configuration = _validated_request(request)
    source = _model_source(configuration)
    source_bytes = source.encode("utf-8")
    with tempfile.TemporaryDirectory(
        prefix="argesim-cifasis-native-", dir=base_directory
    ) as temporary_name:
        workspace = Path(temporary_name)
        for name in ("models", "build", "output", "log"):
            (workspace / name).mkdir()
        model_path = workspace / "models" / f"{_MODEL_NAME}.mo"
        model_path.write_bytes(source_bytes)
        environment = _environment(installation, workspace)
        compile_result = _run_checked(
            (
                str(installation.compile_script),
                _MODEL_NAME,
                str(model_path.parent),
                "",
            ),
            cwd=workspace,
            environment=environment,
        )
        simulation_result = _run_checked(
            (
                str(installation.simulate_script),
                _MODEL_NAME,
                "false",
                "false",
                "false",
            ),
            cwd=workspace,
            environment=environment,
        )
        times, values, raw_name = _read_trajectory(
            workspace / "output" / _MODEL_NAME
        )
    return {
        "schema_version": 1,
        "engine": "CIFASIS/qss-solver",
        "engine_commit": installation.commit,
        "method": configuration["method"],
        "native_method": configuration["solver"],
        "model": {
            "type": _MODEL_TYPE,
            "generated_name": _MODEL_NAME,
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "source": source,
        },
        "trajectory": {"x": {"time": times, "value": values}},
        "metrics": {
            "compile_wall_seconds": compile_result[0],
            "simulation_wall_seconds": simulation_result[0],
            "output_samples": len(times),
        },
        "diagnostics": {
            "compile_stdout": compile_result[1],
            "compile_stderr": compile_result[2],
            "compile_stdout_truncated": compile_result[3],
            "compile_stderr_truncated": compile_result[4],
            "simulation_stdout": simulation_result[1],
            "simulation_stderr": simulation_result[2],
            "simulation_stdout_truncated": simulation_result[3],
            "simulation_stderr_truncated": simulation_result[4],
            "raw_trajectory_file": raw_name,
        },
        "scope": "external execution observation only",
    }


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> None:
    encoded = canonical_json_bytes(payload) + b"\n"
    if len(encoded) > _MAX_OUTPUT_BYTES:
        raise AdapterError("normalized result exceeds the 16 MiB limit")
    parent = path.parent.resolve()
    if not parent.is_dir():
        raise AdapterError("result parent directory does not exist")
    if path.exists() or path.is_symlink():
        raise AdapterError("result path already exists")
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=parent
        )
        temporary = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    except FileExistsError as exc:
        raise AdapterError("result path already exists") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="argesim-cifasis-oracle")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--argesim-oracle-probe", action="store_true")
    mode.add_argument("--argesim-oracle-run", metavar="REQUEST")
    parser.add_argument("--format", choices=("json",), default="json")
    parser.add_argument("--output")
    parser.add_argument("--source-root")
    parser.add_argument("--install-root")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        installation = _resolve_installation(
            arguments.source_root, arguments.install_root
        )
        if arguments.argesim_oracle_probe:
            if arguments.output is not None:
                raise AdapterError("--output is invalid for a capability probe")
            print(
                json.dumps(
                    {
                        "protocol_version": ORACLE_PROTOCOL_VERSION,
                        "engine": "CIFASIS/qss-solver",
                        "engine_commit": installation.commit,
                        "methods": list(_METHODS),
                        "model_formats": ["mu-modelica"],
                    },
                    sort_keys=True,
                    allow_nan=False,
                )
            )
            return 0
        if not arguments.output:
            raise AdapterError("--output is required for an oracle run")
        request_path = Path(arguments.argesim_oracle_run).expanduser().resolve()
        output_path = Path(arguments.output).expanduser()
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
        request = _load_request(request_path)
        result = _execute(installation, request, output_path.parent)
        _write_new_json(output_path, result)
        return 0
    except AdapterError as exc:
        print(f"argesim-cifasis-oracle: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(
            f"argesim-cifasis-oracle: filesystem operation failed: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
