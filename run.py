"""Demo entry point: run baseline heuristics across all scenarios and print a leaderboard."""

import random

from scheduler  import construct
from check      import check
from evaluate   import evaluate
from heuristics import random_priority, edd, spt, lpt, least_slack
from scenarios  import ALL_SCENARIOS


BASELINES = {
    "random":      random_priority,
    "EDD":         edd,
    "SPT":         spt,
    "LPT":         lpt,
    "least_slack": least_slack,
}


def run_one(priority_fn, scenario, admit_fn=None, seed=42):
    random.seed(seed)
    schedule   = construct(scenario["orders"], scenario["kitchen"], priority_fn, admit_fn)
    violations = check(schedule, scenario["orders"], scenario["kitchen"])
    metrics    = evaluate(schedule, scenario["orders"])
    return schedule, violations, metrics


def leaderboard(scenario, heuristics=BASELINES):
    print(f"\n=== {scenario['name']} ===")
    header = f"{'heuristic':<14} {'total_late':>11} {'max_late':>9} {'late':>5} {'sync':>6} {'makespan':>9} {'valid':>6}"
    print(header)
    print("-" * len(header))
    for name, fn in heuristics.items():
        _, violations, m = run_one(fn, scenario)
        flag = "OK" if not violations else f"FAIL({len(violations)})"
        print(
            f"{name:<14} "
            f"{m['total_lateness']:>11.1f} "
            f"{m['max_lateness']:>9.1f} "
            f"{m['num_late']:>5d} "
            f"{m['sync_penalty']:>6.1f} "
            f"{m['makespan']:>9.1f} "
            f"{flag:>6}"
        )


def print_schedule(schedule):
    """Gantt-style text dump of a schedule, sorted by start time."""
    for entry in sorted(schedule, key=lambda e: (e["start"], e["station"])):
        print(f"  t={entry['start']:5.1f} -> {entry['end']:5.1f}  "
              f"[{entry['station']:<8}]  {entry['task']}")


if __name__ == "__main__":
    for scenario in ALL_SCENARIOS:
        leaderboard(scenario)
