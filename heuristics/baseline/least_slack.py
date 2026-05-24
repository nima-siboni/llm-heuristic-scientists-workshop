"""Least slack: due - earliest_start(this task) - remaining_unplaced_work_for_order.

The most urgent task (smallest slack) wins, so we return -slack.
"""

from models.for_llm import State, Task, earliest_start


def least_slack(task: Task, state: State) -> float:
    order = state.orders[task.order]
    remaining = sum(
        state.tasks[tid].duration
        for slot in order.dishes
        for tid in state.dishes[slot].tasks
        if state.tasks[tid].started_at is None
    )
    slack = order.due - earliest_start(task, state) - remaining
    return -slack
