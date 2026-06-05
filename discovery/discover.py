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
import time
import traceback
from datetime import datetime

from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from problem_definition.check     import check
from problem_definition.evaluate  import evaluate
from problem_definition.scenarios import TRAINING
from heuristics.discovered        import RUNS_CSV, save_iteration
from util.infra                   import ScheduleEntry
from discovery.placer             import PriorityFn, construct
from discovery.prompts            import SYSTEM, extract_code, initial_prompt, refine_prompt
from discovery.runtime            import compile_priority, time_limit

load_dotenv()


MODEL          = "openai/gpt-oss-120b"
ITERATIONS     = 5
SCENARIO       = TRAINING
EVAL_TIMEOUT_S = 5     # bound buggy priority() so it can't hang the workshop
MAX_TOKENS     = 1500  # cap on assistant reply length per iteration
MAX_RETRIES    = 5     # API call attempts before giving up on an iteration
BACKOFF_BASE_S = 2.0   # exponential backoff base for 429 / transient errors


def chat_with_retry(client: InferenceClient, history: list[dict]) -> str:
    """Call the chat endpoint, retrying transient failures (esp. HTTP 429).

    Uses exponential backoff (BACKOFF_BASE_S ** attempt). If the server sends
    a Retry-After header on a 429, that wait is honored instead. Raises the
    last error if all attempts are exhausted.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.chat_completion(messages=history, max_tokens=MAX_TOKENS)
            return resp.choices[0].message.content
        except HfHubHTTPError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            transient = status == 429 or (status is not None and status >= 500)
            if not transient or attempt == MAX_RETRIES:
                raise
            retry_after = exc.response.headers.get("Retry-After") if exc.response is not None else None
            wait = float(retry_after) if retry_after else BACKOFF_BASE_S ** attempt
            print(f"--- HTTP {status}; retry {attempt}/{MAX_RETRIES - 1} in {wait:.1f}s ---")
            time.sleep(wait)
    raise RuntimeError("unreachable")  # loop either returns or raises


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
        reply = chat_with_retry(client, history)
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
