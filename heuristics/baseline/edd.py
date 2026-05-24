"""EDD (Earliest Due Date): prioritize tasks belonging to the most urgent order."""

from models.for_llm import State, Task


def edd(task: Task, state: State) -> float:
    return -state.orders[task.order].due
