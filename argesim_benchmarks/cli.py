"""Command-line interface for the ARGESIM reference suite."""

from __future__ import annotations

import argparse
import json

from .catalog import BENCHMARKS
from .runner import BenchmarkTaskError, contract, to_jsonable


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

    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)

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
