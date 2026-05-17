"""Baseline priority functions. Higher score = schedule earlier.

Each function takes (task, state) and returns a float. See scheduler.py for
the schema of task and state.
"""

import random as _random


def random_priority(task, state):
    return _random.random()


def edd(task, state):
    """Earliest Due Date: prioritize tasks belonging to the most urgent order."""
    return -state["orders"][task["order"]]["due"]


def spt(task, state):
    """Shortest Processing Time: prioritize quick tasks first."""
    return -task["duration"]


def lpt(task, state):
    """Longest Processing Time: push long tasks early so they don't block the end."""
    return task["duration"]


def least_slack(task, state):
    """Least slack = due - now - remaining_work_for_order. Returns -slack."""
    oid = task["order"]
    order = state["orders"][oid]
    remaining = 0.0
    for slot in order["dishes"]:
        for tid in state["dishes"][slot]["tasks"]:
            t = state["tasks"][tid]
            if t["status"] != "done":
                remaining += t["duration"]
    slack = order["due"] - state["now"] - remaining
    return -slack
