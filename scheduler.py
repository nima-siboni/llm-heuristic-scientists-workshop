"""Greedy schedule constructor driven by a priority function.

Heuristic contract
------------------
A heuristic is a function:

    priority(task, state) -> float          # higher = schedule earlier

It is called once per eligible task at each decision point. The scheduler
picks the highest-scoring eligible task, assigns it to its required station
(if a slot is free), and repeats until no more tasks can start at the
current time. Then it advances time to the next event.

Optionally, the scheduler accepts an admit gate:

    admit(task, state) -> bool              # False = leave pending (wait)

Use admit to express "this task could start now but I want to hold it back"
(useful for synchronization across dishes in the same order).

Task view (keys present on the dict passed as `task`)
-----------------------------------------------------
    id           str   e.g., "o1.d0.t2"
    name         str   e.g., "grill_patty"
    dish_name    str   e.g., "burger"
    duration     float
    station      str
    order        int   order id
    dish         str   dish slot id, e.g., "o1.d0"
    prereqs      list[str]  task ids that must finish first
    status       "pending" | "running" | "done"
    started_at   float | None
    finished_at  float | None

State view (keys present on the dict passed as `state`)
-------------------------------------------------------
    now       float
    stations  dict[name -> {"capacity", "in_use", "running": [tid, ...]}]
    tasks     dict[tid  -> task view]
    dishes    dict[slot -> {"slot", "name", "order", "tasks": [tid, ...]}]
    orders    dict[oid  -> {"id", "arrival", "due", "dishes": [slot, ...]}]

The heuristic must treat both views as read-only. It must not use information
about a task that is not yet eligible (the scheduler does not hide it, but
peeking into the future defeats the point).
"""

from kitchen import DISHES


def init_state(orders, kitchen):
    tasks = {}
    dishes = {}
    order_dict = {}

    for order in orders:
        oid = order["id"]
        order_dict[oid] = {
            "id":       oid,
            "arrival":  order["arrival"],
            "due":      order["due"],
            "dishes":   [],
        }
        for d_idx, dish_name in enumerate(order["dishes"]):
            dish_slot = f"o{oid}.d{d_idx}"
            dish_task_ids = []
            prev_tid = None
            for t_idx, (name, duration, station) in enumerate(DISHES[dish_name]):
                tid = f"o{oid}.d{d_idx}.t{t_idx}"
                tasks[tid] = {
                    "id":           tid,
                    "name":         name,
                    "dish_name":    dish_name,
                    "duration":     float(duration),
                    "station":      station,
                    "order":        oid,
                    "dish":         dish_slot,
                    "prereqs":      [prev_tid] if prev_tid else [],
                    "status":       "pending",
                    "started_at":   None,
                    "finished_at":  None,
                }
                dish_task_ids.append(tid)
                prev_tid = tid
            dishes[dish_slot] = {
                "slot":   dish_slot,
                "name":   dish_name,
                "order":  oid,
                "tasks":  dish_task_ids,
            }
            order_dict[oid]["dishes"].append(dish_slot)

    stations = {
        name: {"capacity": cap, "in_use": 0, "running": []}
        for name, cap in kitchen.items()
    }

    return {
        "now":       0.0,
        "stations":  stations,
        "tasks":     tasks,
        "dishes":    dishes,
        "orders":    order_dict,
    }


def eligible_tasks(state):
    out = []
    for tid, t in state["tasks"].items():
        if t["status"] != "pending":
            continue
        if state["orders"][t["order"]]["arrival"] > state["now"]:
            continue
        if not all(state["tasks"][p]["status"] == "done" for p in t["prereqs"]):
            continue
        out.append(tid)
    return out


def station_free(state, station_name):
    s = state["stations"][station_name]
    return s["in_use"] < s["capacity"]


def start_task(state, tid):
    t = state["tasks"][tid]
    s = state["stations"][t["station"]]
    t["status"] = "running"
    t["started_at"] = state["now"]
    t["finished_at"] = state["now"] + t["duration"]
    s["in_use"] += 1
    s["running"].append(tid)


def advance_time(state):
    finishing = [
        state["tasks"][tid]["finished_at"]
        for s in state["stations"].values()
        for tid in s["running"]
    ]
    future_arrivals = [
        o["arrival"] for o in state["orders"].values()
        if o["arrival"] > state["now"]
    ]
    candidates = finishing + future_arrivals
    if not candidates:
        return False
    state["now"] = min(candidates)
    for s in state["stations"].values():
        finished_here = [
            tid for tid in s["running"]
            if state["tasks"][tid]["finished_at"] <= state["now"] + 1e-12
        ]
        for tid in finished_here:
            state["tasks"][tid]["status"] = "done"
            s["running"].remove(tid)
            s["in_use"] -= 1
    return True


def all_done(state):
    return all(t["status"] == "done" for t in state["tasks"].values())


def construct(orders, kitchen, priority_fn, admit_fn=None):
    """Return a schedule as a list of {task, station, start, end} dicts."""
    state = init_state(orders, kitchen)
    schedule = []
    safety = 0
    while not all_done(state):
        safety += 1
        if safety > 100000:
            raise RuntimeError("scheduler did not terminate")

        placed = True
        while placed:
            placed = False
            runnable = [
                tid for tid in eligible_tasks(state)
                if station_free(state, state["tasks"][tid]["station"])
            ]
            if admit_fn is not None:
                runnable = [
                    tid for tid in runnable
                    if admit_fn(state["tasks"][tid], state)
                ]
            if not runnable:
                break
            best = max(runnable, key=lambda tid: priority_fn(state["tasks"][tid], state))
            start_task(state, best)
            t = state["tasks"][best]
            schedule.append({
                "task":    best,
                "station": t["station"],
                "start":   t["started_at"],
                "end":     t["finished_at"],
            })
            placed = True

        if not advance_time(state):
            raise RuntimeError("no progress possible (infeasible instance?)")

    return schedule
