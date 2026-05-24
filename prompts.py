"""Prompt construction and LLM-reply parsing for the discovery loop.

Kept separate from `discover.py` so the loop stays focused on orchestration.
"""

import re
import textwrap
from pathlib import Path
from typing import Optional

from models.infra import Scenario


HERE = Path(__file__).parent
PLACER_SRC        = (HERE / "placer.py").read_text()
MODEL_FOR_LLM_SRC = (HERE / "models" / "for_llm.py").read_text()


SYSTEM = f"""\
You are a scheduling researcher. You propose interpretable priority
heuristics for a restaurant-kitchen scheduling problem and express each
one as a single Python function:

    def priority(task, state) -> float

The placer is a list-builder: at each step it picks the highest-priority
eligible task (one whose prereqs are all placed) and commits it to its
station at the earliest feasible time. Higher priority = place this task next.

Rules:
  - reply with one fenced ```python``` block, nothing else
  - the block must define exactly one top-level function named `priority`
  - no imports beyond the Python stdlib; no I/O; no randomness
  - the heuristic must be read-only: do not mutate task or state

The shape of `task` and `state` is defined by models/for_llm.py below; the
placement loop is in placer.py. Treat both as the authoritative spec.
A helper `earliest_start(task, state) -> float` is available in the global
namespace (and defined in models/for_llm.py).

===== models/for_llm.py =====
{MODEL_FOR_LLM_SRC}
===== placer.py =====
{PLACER_SRC}"""


def problem_brief(scenario: Scenario) -> str:
    return textwrap.dedent(f"""
        Problem semantics:
          - An order contains one or more dishes. A dish is a linear chain of tasks
            (task i depends on task i-1). No dependencies across dishes.
          - Lateness is measured per ORDER: an order finishes when all its
            dishes finish, and lateness = max(0, finish - due).
          - Stations have limited capacity (see STATION_CAPACITY above);
            "waiting" is passive (resting/cooling) and doesn't occupy a chef.

        Training orders:
        {scenario.orders}

        Objective: minimize total_lateness = sum of per-order lateness.
    """).strip()


def initial_prompt(scenario: Scenario) -> str:
    return (
        problem_brief(scenario)
        + "\n\nPropose your first heuristic as a `priority(task, state)` function."
    )


def refine_prompt(
    scenario: Scenario,
    prev_code: str,
    prev_value: Optional[float],
    prev_error: Optional[str],
    best_so_far: Optional[float],
) -> str:
    if prev_error:
        feedback = f"The previous attempt raised an exception:\n{prev_error}"
    else:
        feedback = (
            f"Previous attempt total_lateness on the training scenario: {prev_value:.1f}\n"
            f"Best total_lateness so far: {best_so_far:.1f}"
        )
    return (
        problem_brief(scenario)
        + "\n\nPrevious heuristic:\n```python\n" + prev_code + "\n```\n\n"
        + feedback
        + "\n\nPropose an improved `priority(task, state)` function. "
          "Diagnose what likely hurt the previous attempt and fix it. "
          "Keep the function interpretable."
    )


_CODE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL)

def extract_code(reply: str) -> str:
    m = _CODE_RE.search(reply)
    return (m.group(1) if m else reply).strip()
