"""SPT (Shortest Processing Time): prioritize quick steps first."""

from models.for_llm import State, Step


def spt(step: Step, state: State) -> float:
    return -step.duration
