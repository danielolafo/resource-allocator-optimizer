"""Command line interface for the allocation optimizer.

Examples:
    python cli.py generate samples/sample.json
    python cli.py assign samples/sample.json --output samples/result.json
    python cli.py assign samples/sample.json --today 2026-09-16
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from allocator.generate import save_sample
from allocator.models import OptimizationInput
from allocator.optimizer import AllocationProblem, OptimizationResult, optimize


def _read_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def _run(data: dict, today: date | None) -> OptimizationResult:
    parsed = OptimizationInput.model_validate(data)
    problem = AllocationProblem(
        employees=parsed.employees,
        projects=parsed.projects,
        assignments=parsed.assignments,
        today=today,
    )
    return optimize(problem)


def cmd_generate(args) -> int:
    target = save_sample(args.output, today=args.today)
    print(f"Sample dataset written to {target}")
    return 0


def cmd_assign(args) -> int:
    data = _read_json(args.input)
    result = _run(data, args.today)
    payload = result.to_dict()
    _write_json(args.output, payload)
    print(f"Result written to {args.output}")
    print()
    _print_summary(payload)
    return 0


def _print_summary(payload: dict) -> None:
    s = payload["summary"]
    total_avail = sum(s["employeeDaysAvailable"].values())
    print("=" * 64)
    print("RESOURCE ALLOCATION SUMMARY")
    print("=" * 64)
    print(f"Today               : {s['today']}")
    print(f"Planning horizon    : {s['horizonEnd']}")
    print(f"Employees           : {s['totalEmployees']}  "
          f"(occupied: {s['occupiedEmployees']}, idle: {s['idleEmployees']})")
    print(f"Projects            : {s['totalProjects']}")
    print(f"Assigned days       : {s['totalAssignedDays']} / {total_avail}")
    print(f"Average utilization : {s['averageUtilization']:.2%}")
    print(f"Total profit (USD)  : {s['totalProfit']:,.2f}")
    print("-" * 64)
    print("Utilization by employee:")
    for eid, util in s["utilization"].items():
        avail = s["employeeDaysAvailable"].get(eid, 0)
        print(f"  employee {int(eid):>3}: {util:.2%}  ({int(avail)} available days)")
    print("-" * 64)
    print("Assignments produced:")
    for a in payload["assignments"]:
        print(f"  #{a['id']:<4} employee {a['employeeId']:<3} -> project {a['projectId']:<3}"
              f"  {a['startDate']} .. {a['endDate']}")
    if payload["warnings"]:
        print("-" * 64)
        print("Warnings:")
        for w in payload["warnings"]:
            print(f"  - {w}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="allocator", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate a sample dataset")
    gen.add_argument("--output", default="samples/sample.json")
    gen.add_argument("--today", type=date.fromisoformat, default=None)
    gen.set_defaults(func=cmd_generate)

    assign = sub.add_parser("assign", help="Run the optimizer over an input file")
    assign.add_argument("input", type=str)
    assign.add_argument("--output", default="samples/result.json")
    assign.add_argument("--today", type=date.fromisoformat, default=None)
    assign.set_defaults(func=cmd_assign)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())