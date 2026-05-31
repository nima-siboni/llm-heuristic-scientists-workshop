"""LPT (Longest Processing Time): push long steps early so they don't block the end."""

from models.for_llm import State, Step


def lpt(step: Step, state: State) -> float:
    return step.duration
