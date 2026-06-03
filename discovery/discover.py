"""Discovery loop: ask an LLM for a scheduling heuristic, run it through
the simulator, feed total_lateness back, repeat.

Each iteration is persisted under heuristics/discovered/ (one .py file
plus a row in runs.csv).

Usage
-----
    export HF_TOKEN=hf_xxx                       # or set it in .env
    python -m discovery.discover                 # 5 iterations on TRAINING
"""

import os
import traceback
from datetime import datetime

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

from problem_definition.check     import check
from problem_definition.evaluate  import evaluate
from problem_definition.scenarios import TRAINING
from heuristics.discovered        import RUNS_CSV, save_iteration
from util.infra                   import ScheduleEntry
from discovery.placer             import PriorityFn, construct
from discovery.prompts            import SYSTEM, extract_code, initial_prompt, refine_prompt
from discovery.runtime            import compile_priority, time_limit
from discovery.tools              import chat_with_tools

load_dotenv()


MODEL          = "openai/gpt-oss-120b"
ITERATIONS     = 5
SCENARIO       = TRAINING
EVAL_TIMEOUT_S = 5     # bound buggy priority() so it can't hang the workshop
MAX_TOKENS     = 4096  # cap on assistant reply length per iteration (reasoning is verbose)


def build_schedule(priority_fn: PriorityFn) -> list[ScheduleEntry]:
    """Run the placer for the current SCENARIO; verify the result is valid."""
    schedule   = construct(SCENARIO.orders, SCENARIO.kitchen, priority_fn)
    violations = check(schedule, SCENARIO.orders, SCENARIO.kitchen)
    if violations:
        raise ValueError(f"schedule violates constraints: {violations[:3]}")
    return schedule


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
        reply = chat_with_tools(client, history, SCENARIO, MAX_TOKENS)
        code  = extract_code(reply)
        print("--- proposed heuristic ---")
        print(code)

        prev_value, prev_error = None, None
        value:       float | None = None
        error_class: str   | None = None
        try:
            with time_limit(EVAL_TIMEOUT_S):
                fn       = compile_priority(code)
                schedule = build_schedule(fn)
                value    = evaluate(schedule, SCENARIO.orders)
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
