"""Command-line interface for the ARGESIM reference suite."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import BENCHMARKS
from .oracles.cli import add_oracle_commands, handle_oracle_command
from .runner import BenchmarkTaskError, contract, run_suite, to_jsonable


def _json_object(text: str) -> dict[str, object]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not isinstance(value, dict):
        raise argparse.ArgumentTypeError("expected a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="argesim")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list")

    describe = commands.add_parser("describe")
    describe.add_argument("benchmark")

    run = commands.add_parser("run")
    run.add_argument("benchmark")
    run.add_argument("task")
    run.add_argument("--kwargs-json", type=_json_object, default={})

    suite = commands.add_parser("run-suite")
    suite.add_argument("--profile", choices=("smoke", "definition"), default="smoke")
    suite.add_argument("--benchmark", action="append", dest="benchmarks")
    suite.add_argument("--fail-fast", action="store_true")

    performance = commands.add_parser("run-performance")
    performance.add_argument("--profile", choices=("smoke", "definition"),
                             default="definition")
    performance.add_argument("--benchmark", action="append", dest="benchmarks")
    performance.add_argument("--task", action="append", dest="tasks",
                             help="registered BENCHMARK:TASK, repeatable")
    performance.add_argument("--warmup", type=int, default=1)
    performance.add_argument("--repetitions", type=int, default=9)
    performance.add_argument("--timeout-s", type=float, default=3600.0)
    performance.add_argument("--output-dir", type=Path, required=True)
    performance.add_argument("--fail-fast", action="store_true")

    add_oracle_commands(commands)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)

    if arguments.command == "oracle":
        try:
            return handle_oracle_command(arguments)
        except (ValueError, OSError) as exc:
            raise SystemExit(str(exc)) from exc

    if arguments.command == "list":
        payload = [
            {
                "id": entry.identifier,
                "title": entry.title,
                "status": entry.status.value,
            }
            for entry in BENCHMARKS
        ]
        print(json.dumps(payload, indent=2, allow_nan=False))
        return 0

    if arguments.command == "run-suite":
        try:
            report = run_suite(
                profile=arguments.profile,
                benchmarks=tuple(arguments.benchmarks) if arguments.benchmarks else None,
                fail_fast=arguments.fail_fast,
            )
        except BenchmarkTaskError as exc:
            raise SystemExit(str(exc)) from exc
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 1 if report["failed"] else 0

    if arguments.command == "run-performance":
        from .performance import run_performance
        try:
            report = run_performance(
                output_dir=arguments.output_dir,
                profile=arguments.profile,
                benchmarks=tuple(arguments.benchmarks) if arguments.benchmarks else None,
                tasks=tuple(arguments.tasks) if arguments.tasks else None,
                warmup=arguments.warmup,
                repetitions=arguments.repetitions,
                timeout_s=arguments.timeout_s,
                fail_fast=arguments.fail_fast,
            )
        except (BenchmarkTaskError, ValueError, OSError) as exc:
            raise SystemExit(str(exc)) from exc
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 1 if report["failed"] else 0

    try:
        benchmark_contract = contract(arguments.benchmark)
        if arguments.command == "describe":
            definition = benchmark_contract.definition
            payload = {
                "id": definition.identifier,
                "title": definition.title,
                "status": definition.status.value,
                "model_classes": [value.value for value in definition.model_classes],
                "tasks": sorted(benchmark_contract.tasks),
            }
            print(json.dumps(payload, indent=2))
            return 0

        result = benchmark_contract.run(arguments.task, arguments.kwargs_json)
        print(json.dumps(to_jsonable(result), indent=2, sort_keys=True, allow_nan=False))
        return 0
    except BenchmarkTaskError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
