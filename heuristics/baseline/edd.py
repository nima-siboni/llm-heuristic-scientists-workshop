"""EDD (Earliest Due Date): prioritize steps belonging to the most urgent order."""

from problem_definition.model import State, Step


def edd(step: Step, state: State) -> float:
    return -step.dish.order.due
