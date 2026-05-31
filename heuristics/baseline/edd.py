"""EDD (Earliest Due Date): prioritize steps belonging to the most urgent order."""

from models.for_llm import State, Step


def edd(step: Step, state: State) -> float:
    return -step.dish.order.due
