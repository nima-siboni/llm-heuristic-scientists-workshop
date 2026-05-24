"""Domain model that the LLM-authored heuristic sees and reasons about.

A heuristic is a function `priority(task: Task, state: State) -> float`
(higher priority = place this task next). Everything in this file is
something the heuristic might read; nothing in here is implementation
plumbing.

A dish is a linear chain of RecipeSteps; within a dish, step i depends on
step i-1. There are no cross-dish dependencies.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Static configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RecipeStep:
    name:     str
    duration: float
    station:  str


DISHES: dict[str, list[RecipeStep]] = {
    "burger": [
        RecipeStep("prep_patty",      3, "prep"),
        RecipeStep("grill_patty",     8, "grill"),
        RecipeStep("toast_bun",       2, "oven"),
        RecipeStep("assemble_burger", 2, "plating"),
    ],
    "fries": [
        RecipeStep("cut_potatoes", 3, "prep"),
        RecipeStep("fry_potatoes", 5, "fryer"),
        RecipeStep("season_fries", 1, "plating"),
    ],
    "salad": [
        RecipeStep("chop_veg",    4, "prep"),
        RecipeStep("mix_salad",   2, "prep"),
        RecipeStep("plate_salad", 1, "plating"),
    ],
    "steak": [
        RecipeStep("season_steak", 2,  "prep"),
        RecipeStep("grill_steak",  12, "grill"),
        RecipeStep("rest_steak",   5,  "waiting"),
        RecipeStep("plate_steak",  2,  "plating"),
    ],
    "pasta": [
        RecipeStep("boil_pasta",    8, "stove"),
        RecipeStep("cook_sauce",    6, "stove"),
        RecipeStep("combine_pasta", 2, "stove"),
        RecipeStep("plate_pasta",   1, "plating"),
    ],
    "soup": [
        RecipeStep("chop_veg_soup", 3,  "prep"),
        RecipeStep("simmer_soup",   10, "stove"),
        RecipeStep("plate_soup",    1,  "plating"),
    ],
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
# Runtime state (built incrementally as tasks are placed)
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """One cooking step. ID format: "o{order}.d{dish_idx}.t{step_idx}".

    A task is "placed" once the placer commits it; that's when started_at
    and finished_at get set. Before placement, both are None.
    """
    id:           str
    name:         str
    dish_name:    str
    duration:     float
    station:      str
    order:        int             # parent order id
    dish:         str             # parent dish slot id, e.g. "o1.d0"
    prereqs:      list[str]       # task ids that must be placed before this one
    started_at:   float | None = None
    finished_at:  float | None = None


@dataclass
class Station:
    """A cooking station with finite capacity. slot_free_times[i] is the
    earliest time at which slot i becomes free; initialised to all zeros
    and updated each time a task is placed on the station.
    """
    name:            str
    capacity:        int
    slot_free_times: list[float] = field(default_factory=list)


@dataclass
class DishInstance:
    """A dish belonging to a specific order."""
    slot:  str                    # e.g. "o1.d0"
    name:  str                    # dish name (key into DISHES)
    order: int                    # parent order id
    tasks: list[str]              # task ids in execution order


@dataclass
class OrderState:
    """An order's runtime view (dish slot ids instead of dish names)."""
    id:      int
    arrival: float
    due:     float
    dishes:  list[str]            # dish slot ids, e.g. ["o1.d0", "o1.d1"]


@dataclass
class State:
    stations: dict[str, Station]      # keyed by station name
    tasks:    dict[str, Task]         # keyed by task id; includes the task being prioritized
    dishes:   dict[str, DishInstance] # keyed by dish slot id
    orders:   dict[int, OrderState]   # keyed by order id


# ---------------------------------------------------------------------------
# Helper available to heuristics
# ---------------------------------------------------------------------------

def earliest_start(task: Task, state: State) -> float:
    """Earliest time `task` could start if placed next, given the placements
    committed so far.

      = max(latest prereq finish_time, earliest free slot on its station,
            order arrival time)
    """
    prereq_finish = max(
        (state.tasks[p].finished_at for p in task.prereqs
         if state.tasks[p].finished_at is not None),
        default=0.0,
    )
    station = state.stations[task.station]
    station_free = min(station.slot_free_times) if station.slot_free_times else 0.0
    arrival = state.orders[task.order].arrival
    return max(prereq_finish, station_free, arrival)
