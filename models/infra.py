"""Orchestration-only types. These are how the discovery loop and runner
hand a problem instance to the placer and read back its output. The
LLM-authored heuristic never sees any of these — they live outside its
priority(task, state) contract.
"""

from dataclasses import dataclass


@dataclass
class Order:
    """A customer ticket: one or more dishes due by a deadline."""
    id:      int
    arrival: float
    due:     float
    dishes:  list[str]            # dish names (keys into models.for_llm.DISHES)


@dataclass
class Scenario:
    """A problem instance: a kitchen (station -> capacity) and a list of orders."""
    name:    str
    kitchen: dict[str, int]
    orders:  list[Order]


@dataclass
class ScheduleEntry:
    """One row of a built schedule. Produced by the placer, consumed by check/evaluate."""
    task:    str                  # task id
    station: str
    start:   float
    end:     float
