"""LPT (Longest Processing Time): push long steps early so they don't block the end."""

from problem_definition.model import State, Step


def lpt(step: Step, state: State) -> float:
    return step.duration
