"""Random baseline — assigns each step a random priority."""

import random as _random

from problem_definition.model import State, Step


def random_priority(step: Step, state: State) -> float:
    return _random.random()
