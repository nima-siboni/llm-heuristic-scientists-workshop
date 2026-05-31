"""Least slack: due - earliest_start(this step) - remaining_unplaced_work_for_order.

The most urgent step (smallest slack) wins, so we return -slack.
"""

from problem_definition.model import State, Step, earliest_start


def least_slack(step: Step, state: State) -> float:
    order = step.dish.order
    remaining = sum(
        s.duration
        for d in order.dishes
        for s in d.steps
        if s.started_at is None
    )
    slack = order.due - earliest_start(step, state) - remaining
    return -slack
