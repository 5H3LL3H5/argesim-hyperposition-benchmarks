"""CLI wiring for optional external solver oracles."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .base import OracleStatus
from .cifasis import CIFASIS_PINNED_COMMIT, CifasisOracle


def add_oracle_commands(commands: Any) -> None:
    oracle = commands.add_parser("oracle")
    operations = oracle.add_subparsers(dest="oracle_command", required=True)
    for name in ("probe", "capabilities"):
        operation = operations.add_parser(name)
        operation.add_argument("oracle", choices=("cifasis",))
        _add_common_options(operation)

    run = operations.add_parser("run")
    run.add_argument("oracle", choices=("cifasis",))
    _add_common_options(run)
    run.add_argument("--request", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--timeout-s", type=float, default=300.0)


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--executable",
        help=(
            "external adapter executable; otherwise use "
            "ARGESIM_CIFASIS_ORACLE or PATH"
        ),
    )
    parser.add_argument(
        "--adapter-arg",
        action="append",
        default=[],
        help="one fixed adapter argument, repeatable",
    )
    parser.add_argument("--expected-commit", default=CIFASIS_PINNED_COMMIT)
    parser.add_argument("--probe-timeout-s", type=float, default=10.0)


def _oracle(arguments: argparse.Namespace) -> CifasisOracle:
    executable: Sequence[str] | None = None
    if arguments.executable:
        executable = (arguments.executable, *arguments.adapter_arg)
    elif arguments.adapter_arg:
        raise ValueError("--adapter-arg requires --executable")
    return CifasisOracle(
        executable,
        expected_commit=arguments.expected_commit,
        probe_timeout_seconds=arguments.probe_timeout_s,
    )


def handle_oracle_command(arguments: argparse.Namespace) -> int:
    oracle = _oracle(arguments)
    if arguments.oracle_command in ("probe", "capabilities"):
        print(
            json.dumps(
                oracle.capabilities().to_dict(),
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
        )
        return 0

    try:
        payload = json.loads(arguments.request.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read oracle request: {exc}") from exc
    if not isinstance(payload, dict):
        raise TypeError("oracle request must be a JSON object")
    result = oracle.run(
        payload,
        arguments.output_dir,
        timeout_seconds=arguments.timeout_s,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True, allow_nan=False))
    if result.succeeded:
        return 0
    if result.status in {
        OracleStatus.UNAVAILABLE,
        OracleStatus.BUILD_REQUIRED,
        OracleStatus.UNSUPPORTED_METHOD,
    }:
        return 2
    return 1
