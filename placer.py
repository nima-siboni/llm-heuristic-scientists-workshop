"""Greedy task placer driven by a priority function.

A heuristic is `priority(task, state) -> float` (higher = place next). The
placer repeatedly picks the highest-priority eligible task (one whose
prereqs are all placed) and commits it to its station at the earliest time
allowed by its prereqs, the station's free slots, and the order's arrival.

There is no global clock — each task's start/finish times are computed at
the moment it is placed. The heuristic sees the full state (placements so
far, station availability, all orders and tasks) and decides which task to
commit next.
"""

from typing import Callable

from models.for_llm import (
    DISHES,
    DishInstance,
    OrderState,
    State,
    Station,
    Task,
    earliest_start,
)
from models.infra import Order, ScheduleEntry


PriorityFn = Callable[[Task, State], float]


def init_state(orders: list[Order], kitchen: dict[str, int]) -> State:
    tasks:        dict[str, Task]         = {}
    dishes:       dict[str, DishInstance] = {}
    order_states: dict[int, OrderState]   = {}

    for order in orders:
        oid = order.id
        order_states[oid] = OrderState(
            id=oid, arrival=order.arrival, due=order.due, dishes=[],
        )
        for d_idx, dish_name in enumerate(order.dishes):
            dish_slot = f"o{oid}.d{d_idx}"
            task_ids: list[str] = []
            prev_tid: str | None = None
            for t_idx, step in enumerate(DISHES[dish_name]):
                tid = f"o{oid}.d{d_idx}.t{t_idx}"
                tasks[tid] = Task(
                    id        = tid,
                    name      = step.name,
                    dish_name = dish_name,
                    duration  = float(step.duration),
                    station   = step.station,
                    order     = oid,
                    dish      = dish_slot,
                    prereqs   = [prev_tid] if prev_tid else [],
                )
                task_ids.append(tid)
                prev_tid = tid
            dishes[dish_slot] = DishInstance(
                slot=dish_slot, name=dish_name, order=oid, tasks=task_ids,
            )
            order_states[oid].dishes.append(dish_slot)

    stations = {
        name: Station(name=name, capacity=cap, slot_free_times=[0.0] * cap)
        for name, cap in kitchen.items()
    }
    return State(stations=stations, tasks=tasks, dishes=dishes, orders=order_states)


def eligible_tasks(state: State) -> list[str]:
    """Unplaced tasks whose prereqs are all placed."""
    return [
        tid for tid, t in state.tasks.items()
        if t.started_at is None
        and all(state.tasks[p].started_at is not None for p in t.prereqs)
    ]


def place(state: State, tid: str) -> ScheduleEntry:
    """Commit a task to its station at the earliest feasible time."""
    t = state.tasks[tid]
    s = state.stations[t.station]
    start = earliest_start(t, state)
    end   = start + t.duration
    slot_idx = min(range(len(s.slot_free_times)), key=lambda i: s.slot_free_times[i])
    s.slot_free_times[slot_idx] = end
    t.started_at  = start
    t.finished_at = end
    return ScheduleEntry(task=tid, station=t.station, start=start, end=end)


def construct(orders: list[Order], kitchen: dict[str, int], priority_fn: PriorityFn) -> list[ScheduleEntry]:
    state = init_state(orders, kitchen)
    schedule: list[ScheduleEntry] = []
    total = len(state.tasks)
    while len(schedule) < total:
        runnable = eligible_tasks(state)
        if not runnable:
            raise RuntimeError("no progress possible (cycle or infeasible inputs?)")
        # Primary key: user-defined priority. Tie-break: prefer the task that
        # can start soonest — among equivalents, never starve the kitchen.
        best = max(runnable, key=lambda tid: (
            priority_fn(state.tasks[tid], state),
            -earliest_start(state.tasks[tid], state),
        ))
        schedule.append(place(state, best))
    return schedule
