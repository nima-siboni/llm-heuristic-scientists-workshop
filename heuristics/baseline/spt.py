"""SPT (Shortest Processing Time): prioritize quick steps first."""

from problem_definition.model import State, Step


def spt(step: Step, state: State) -> float:
    return -step.duration
