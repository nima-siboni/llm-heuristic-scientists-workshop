"""SPT (Shortest Processing Time): prioritize quick tasks first."""

from models.for_llm import State, Task


def spt(task: Task, state: State) -> float:
    return -task.duration
