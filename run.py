"""Demo entry point: run baseline heuristics across all scenarios and print a leaderboard."""

import random

from check      import check
from evaluate   import evaluate
from heuristics.baseline import edd, least_slack, lpt, random_priority, spt
from models.infra import ScheduleEntry, Scenario
from scenarios  import ALL_SCENARIOS
from placer     import PriorityFn, construct


BASELINES: dict[str, PriorityFn] = {
    "random":      random_priority,
    "EDD":         edd,
    "SPT":         spt,
    "LPT":         lpt,
    "least_slack": least_slack,
}


def run_one(priority_fn: PriorityFn, scenario: Scenario, seed: int = 42):
    random.seed(seed)
    schedule       = construct(scenario.orders, scenario.kitchen, priority_fn)
    violations     = check(schedule, scenario.orders, scenario.kitchen)
    total_lateness = evaluate(schedule, scenario.orders)
    return schedule, violations, total_lateness


def leaderboard(scenario: Scenario, heuristics: dict[str, PriorityFn] = BASELINES) -> None:
    print(f"\n=== {scenario.name} ===")
    header = f"{'heuristic':<14} {'total_lateness':>15} {'valid':>6}"
    print(header)
    print("-" * len(header))
    for name, fn in heuristics.items():
        _, violations, total = run_one(fn, scenario)
        flag = "OK" if not violations else f"FAIL({len(violations)})"
        print(f"{name:<14} {total:>15.1f} {flag:>6}")


def print_schedule(schedule: list[ScheduleEntry]) -> None:
    """Gantt-style text dump of a schedule, sorted by start time."""
    for entry in sorted(schedule, key=lambda e: (e.start, e.station)):
        print(f"  t={entry.start:5.1f} -> {entry.end:5.1f}  "
              f"[{entry.station:<8}]  {entry.step}")


if __name__ == "__main__":
    for scenario in ALL_SCENARIOS:
        leaderboard(scenario)
