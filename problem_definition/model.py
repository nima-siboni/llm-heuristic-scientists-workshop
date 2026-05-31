"""Domain model that the LLM-authored heuristic sees and reasons about.

A heuristic is a function `priority(step: Step, state: State) -> float`
(higher priority = place this step next). The object graph is:

    Order -> dishes -> Dish -> steps -> Step

Each Step knows its `dish` (back-ref) and its `prereq` (the step before it
in the same dish, or None if it's the dish's first step). There are no
cross-dish dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Static configuration
# ---------------------------------------------------------------------------

Recipe = list[tuple[float, str]]    # ordered chain of (duration, station) steps


RECIPES: dict[str, Recipe] = {
    "burger": [(3, "prep"), (8, "grill"), (2, "oven"), (2, "plating")],
    "fries":  [(3, "prep"), (5, "fryer"), (1, "plating")],
    "salad":  [(4, "prep"), (2, "prep"), (1, "plating")],
    "steak":  [(2, "prep"), (12, "grill"), (5, "waiting"), (2, "plating")],
    "pasta":  [(8, "stove"), (6, "stove"), (2, "stove"), (1, "plating")],
    "soup":   [(3, "prep"), (10, "stove"), (1, "plating")],
}

# "waiting" represents passive steps (resting meat, cooling) — no chef occupied.
STATION_CAPACITY: dict[str, int] = {
    "prep":    2,
    "grill":   1,
    "oven":    1,
    "fryer":   1,
    "stove":   1,
    "plating": 1,
    "waiting": 99,
}


# ---------------------------------------------------------------------------
# Runtime state — an Order -> Dish -> Step object graph, built once by the
# placer and then mutated (timing fields, station slot_free_times) as steps
# are placed.
# ---------------------------------------------------------------------------

@dataclass
class Order:
    id:      int
    arrival: float
    due:     float
    dishes:  list[Dish]      = field(default_factory=list)


@dataclass
class Dish:
    """A dish belonging to a specific order.

    `order` is a back-reference to the parent Order.
    `steps` are in execution order; step[i].prereq == step[i-1].
    """
    name:  str                                  # recipe name (key into RECIPES)
    order: Order             = field(repr=False, compare=False)
    steps: list[Step]        = field(default_factory=list)


@dataclass
class Step:
    """One cooking step belonging to a dish.

    `dish` is a back-reference to the parent Dish.
    `prereq` is the step that must finish before this one starts, or None
    if this is the dish's first step.
    A step is "placed" once the placer commits it; that's when started_at
    and finished_at get set. Before placement, both are None.
    """
    id:          str
    duration:    float
    station:     str
    dish:        Dish               = field(repr=False, compare=False)
    prereq:      Step | None        = field(default=None, repr=False, compare=False)
    started_at:  float | None       = None
    finished_at: float | None       = None


@dataclass
class Station:
    """A cooking station with finite capacity. slot_free_times[i] is the
    earliest time at which slot i becomes free; initialised to all zeros
    and updated each time a step is placed on the station.
    """
    capacity:        int
    slot_free_times: list[float] = field(default_factory=list)


@dataclass
class State:
    stations: dict[str, Station]    # keyed by station name
    orders:   list[Order]


# ---------------------------------------------------------------------------
# Helper available to heuristics
# ---------------------------------------------------------------------------

def earliest_start(step: Step, state: State) -> float:
    """Earliest time `step` could start if placed next, given placements so far.

      = max(prereq finish_time (0 if no prereq),
            earliest free slot on its station,
            order arrival time)
    """
    prereq_finish = 0.0
    if step.prereq is not None and step.prereq.finished_at is not None:
        prereq_finish = step.prereq.finished_at
    station = state.stations[step.station]
    station_free = min(station.slot_free_times) if station.slot_free_times else 0.0
    return max(prereq_finish, station_free, step.dish.order.arrival)
