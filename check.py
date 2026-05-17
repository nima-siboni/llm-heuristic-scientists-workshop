"""Independent constraint validator. Verifies any schedule, regardless of how it was built."""

from kitchen import DISHES


def check(schedule, orders, kitchen):
    """Return a list of violation strings. Empty list means the schedule is valid.

    Checks:
      - every expected task appears exactly once
      - tasks run on their required station
      - durations match the recipe
      - intra-dish precedence is respected
      - tasks do not start before their order arrives
      - station capacity is never exceeded
    """
    EPS = 1e-9
    violations = []

    expected = {}
    for order in orders:
        oid = order["id"]
        for d_idx, dish_name in enumerate(order["dishes"]):
            prev_tid = None
            for t_idx, (name, duration, station) in enumerate(DISHES[dish_name]):
                tid = f"o{oid}.d{d_idx}.t{t_idx}"
                expected[tid] = {
                    "duration":  float(duration),
                    "station":   station,
                    "prev":      prev_tid,
                    "arrival":   order["arrival"],
                }
                prev_tid = tid

    by_tid = {}
    for entry in schedule:
        tid = entry["task"]
        if tid in by_tid:
            violations.append(f"task {tid} scheduled more than once")
        by_tid[tid] = entry

    for tid, e in expected.items():
        if tid not in by_tid:
            violations.append(f"task {tid} not scheduled")
            continue
        s = by_tid[tid]
        if abs((s["end"] - s["start"]) - e["duration"]) > EPS:
            violations.append(
                f"task {tid} duration {s['end']-s['start']:.3f} != expected {e['duration']:.3f}"
            )
        if s["station"] != e["station"]:
            violations.append(
                f"task {tid} on station {s['station']} but recipe needs {e['station']}"
            )
        if s["start"] < e["arrival"] - EPS:
            violations.append(
                f"task {tid} starts at {s['start']:.3f} before arrival {e['arrival']}"
            )
        if e["prev"] is not None and e["prev"] in by_tid:
            prev_end = by_tid[e["prev"]]["end"]
            if s["start"] < prev_end - EPS:
                violations.append(
                    f"task {tid} starts at {s['start']:.3f} before prereq {e['prev']} ends at {prev_end:.3f}"
                )

    for station, capacity in kitchen.items():
        events = []
        for entry in schedule:
            if entry["station"] == station:
                events.append((entry["start"], +1))
                events.append((entry["end"],   -1))
        # At the same instant, process finishes (-1) before starts (+1)
        events.sort(key=lambda e: (e[0], e[1]))
        in_use = 0
        for t, delta in events:
            in_use += delta
            if in_use > capacity:
                violations.append(
                    f"station {station} over capacity at t={t}: {in_use} > {capacity}"
                )
                break

    return violations
