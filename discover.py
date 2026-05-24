"""Discovery loop: ask GPT-OSS-120B (via Hugging Face) for a scheduling
heuristic, run it through the simulator, feed total_lateness back, repeat.

Each iteration is persisted under heuristics/discovered/ (one .py file plus
a row in runs.csv); see heuristics.discovered.save_iteration for details.

Usage
-----
    export HF_TOKEN=hf_xxx
    python discover.py                       # 5 iterations on the training scenario

Requires
--------
    pip install huggingface_hub
"""

import os
import signal
import traceback
from contextlib import contextmanager
from datetime import datetime

from huggingface_hub import InferenceClient

from check                  import check
from evaluate               import evaluate
from heuristics.discovered  import RUNS_CSV, save_iteration
from models.for_llm         import State, Task, earliest_start
from models.infra           import ScheduleEntry
from placer                 import PriorityFn, construct
from prompts                import SYSTEM, extract_code, initial_prompt, refine_prompt
from scenarios              import TRAINING


MODEL          = "openai/gpt-oss-120b"
ITERATIONS     = 5
SCENARIO       = TRAINING
EVAL_TIMEOUT_S = 5     # bound buggy priority() so it can't hang the workshop


class HeuristicTimeoutError(TimeoutError):
    pass


@contextmanager
def time_limit(seconds: int):
    """Raise HeuristicTimeoutError if the wrapped block runs longer than
    `seconds`. Unix-only (uses SIGALRM); main thread only."""
    def _handler(signum, frame):
        raise HeuristicTimeoutError(f"exceeded {seconds}s")
    old = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def compile_priority(code: str) -> PriorityFn:
    """Exec the generated code and return the `priority` callable. Workshop-grade
    sandboxing only — this is `exec` on LLM output, run it in a throwaway env.
    Task, State, and earliest_start are injected so the LLM can use them."""
    ns: dict = {"Task": Task, "State": State, "earliest_start": earliest_start}
    exec(compile(code, "<llm-heuristic>", "exec"), ns)
    fn = ns.get("priority")
    if not callable(fn):
        raise ValueError("generated code did not define a callable `priority`")
    return fn


def build_schedule(priority_fn: PriorityFn) -> list[ScheduleEntry]:
    """Build a schedule and verify it satisfies the kitchen's constraints."""
    schedule   = construct(SCENARIO.orders, SCENARIO.kitchen, priority_fn)
    violations = check(schedule, SCENARIO.orders, SCENARIO.kitchen)
    if violations:
        raise ValueError(f"schedule violates constraints: {violations[:3]}")
    return schedule


def score(schedule: list[ScheduleEntry]) -> float:
    return evaluate(schedule, SCENARIO.orders)


def discover() -> None:
    client = InferenceClient(model=MODEL, token=os.environ["HF_TOKEN"])
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    history = [{"role": "system", "content": SYSTEM}]
    prompt  = initial_prompt(SCENARIO)

    best_value: float | None = None
    best_code:  str   | None = None
    best_iter:  int   | None = None
    prev_value, prev_error = None, None

    for it in range(1, ITERATIONS + 1):
        print(f"\n=== iteration {it} ===")

        if it > 1:
            prompt = refine_prompt(SCENARIO, prev_value, prev_error, best_value)

        history.append({"role": "user", "content": prompt})
        reply = client.chat_completion(messages=history, max_tokens=1500).choices[0].message.content
        history.append({"role": "assistant", "content": reply})

        code = extract_code(reply)
        print("--- proposed heuristic ---")
        print(code)

        prev_value, prev_error = None, None
        value:       float | None = None
        error_class: str   | None = None
        try:
            with time_limit(EVAL_TIMEOUT_S):
                fn       = compile_priority(code)
                schedule = build_schedule(fn)
                value    = score(schedule)
        except Exception as exc:
            prev_error  = traceback.format_exc(limit=3)
            error_class = type(exc).__name__
            print(f"--- failed ---\n{prev_error}")
        else:
            prev_value = value
            print(f"--- total_lateness = {value:.1f}")
            if best_value is None or value < best_value:
                best_value, best_code, best_iter = value, code, it
                print(f"--- new best (iter {it}) ---")

        save_iteration(
            run_id         = run_id,
            scenario       = SCENARIO.name,
            model          = MODEL,
            iteration      = it,
            code           = code,
            total_lateness = value,
            error          = error_class,
        )

    print("\n=== best heuristic ===")
    if best_code is None:
        print(f"no successful heuristic discovered (run_id={run_id})")
    else:
        print(f"from iteration {best_iter}, total_lateness = {best_value:.1f}")
        print(best_code)
    print(f"\nrun_id={run_id}, see {RUNS_CSV}")


if __name__ == "__main__":
    discover()
