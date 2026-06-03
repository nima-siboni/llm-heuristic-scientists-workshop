"""OpenRouter discovery loop: ask an LLM for a scheduling heuristic, run it
through the simulator, feed total_lateness back, repeat.

This is the OpenRouter variant of discovery.discover. Each iteration is
persisted under heuristics/discovered/ (one .py file plus a row in runs.csv).

Usage
-----
    export OPENROUTER_API_KEY=sk-or-v1-xxx       # or set it in .env
    python -m discovery.discover_openrouter      # 5 iterations on TRAINING
"""

import json
import os
import time
import traceback
from datetime import datetime
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from problem_definition.check     import check
from problem_definition.evaluate  import evaluate
from problem_definition.scenarios import TRAINING
from heuristics.discovered        import RUNS_CSV, save_iteration
from util.infra                   import ScheduleEntry
from discovery.placer             import PriorityFn, construct
from discovery.prompts            import SYSTEM, extract_code, initial_prompt, refine_prompt
from discovery.runtime            import compile_priority, time_limit

load_dotenv()


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL          = "nvidia/nemotron-3-super-120b-a12b:free"
ITERATIONS     = 5
SCENARIO       = TRAINING
EVAL_TIMEOUT_S = 5     # bound buggy priority() so it can't hang the workshop
MAX_TOKENS     = 1500  # cap on assistant reply length per iteration
RETRIES        = 3


def chat_completion(messages: list[dict[str, str]]) -> str:
    """Call OpenRouter's OpenAI-compatible chat-completions endpoint."""
    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
    }).encode("utf-8")
    request = Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/",
            "X-Title": "Bliss heuristic discovery",
        },
        method="POST",
    )
    for attempt in range(1, RETRIES + 1):
        try:
            with urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code not in {429, 503} or attempt == RETRIES:
                raise RuntimeError(f"OpenRouter request failed ({exc.code}): {body}") from exc
            wait_s = 2 ** attempt
            print(f"OpenRouter returned {exc.code}; retrying in {wait_s}s...")
            time.sleep(wait_s)
    return data["choices"][0]["message"]["content"]


def build_schedule(priority_fn: PriorityFn) -> list[ScheduleEntry]:
    """Run the placer for the current SCENARIO; verify the result is valid."""
    schedule   = construct(SCENARIO.orders, SCENARIO.kitchen, priority_fn)
    violations = check(schedule, SCENARIO.orders, SCENARIO.kitchen)
    if violations:
        raise ValueError(f"schedule violates constraints: {violations[:3]}")
    return schedule


def discover() -> None:
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
        reply = chat_completion(history)
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
