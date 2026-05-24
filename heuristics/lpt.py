"""LPT (Longest Processing Time): push long tasks early so they don't block the end."""

from models.for_llm import State, Task


def lpt(task: Task, state: State) -> float:
    return task.duration
