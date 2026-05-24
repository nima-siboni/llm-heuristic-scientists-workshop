"""Schedule scoring. Returns total_lateness, the sum of per-order lateness.

Lateness for an order = max(0, completion - due). The kitchen wants this
number as low as possible.
"""

from models.for_llm import DISHES
from models.infra   import Order, ScheduleEntry


def evaluate(schedule: list[ScheduleEntry], orders: list[Order]) -> float:
    by_tid = {entry.task: entry for entry in schedule}

    total = 0.0
    for order in orders:
        oid = order.id
        order_ends: list[float] = []
        for d_idx, dish_name in enumerate(order.dishes):
            for t_idx, _ in enumerate(DISHES[dish_name]):
                tid = f"o{oid}.d{d_idx}.t{t_idx}"
                if tid in by_tid:
                    order_ends.append(by_tid[tid].end)
        if order_ends:
            total += max(0.0, max(order_ends) - order.due)
    return total
