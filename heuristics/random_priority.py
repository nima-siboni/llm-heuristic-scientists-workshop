"""Random baseline — assigns each task a random priority."""

import random as _random

from models.for_llm import State, Task


def random_priority(task: Task, state: State) -> float:
    return _random.random()
