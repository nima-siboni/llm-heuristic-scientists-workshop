"""LLM-callable tools used during discovery.

One tool: `run_python(code)`. The model emits it whenever it wants to
inspect the scenario (distributions, station load, dish mixes, etc.)
before committing a heuristic. Stdout is returned as the tool result.

`chat_with_tools` wraps the request/response loop: keep dispatching tool
calls until the model stops asking and returns a normal message.
"""

import io
import json
from contextlib import redirect_stdout

from huggingface_hub import InferenceClient

from discovery.placer            import init_state
from discovery.runtime           import time_limit
from problem_definition.model    import earliest_start
from util.infra                  import Scenario


EXEC_TIMEOUT_S          = 5
MAX_TOOL_CALLS_PER_TURN = 8
OUTPUT_LIMIT            = 4000


RUN_PYTHON = {
    "type": "function",
    "function": {
        "name": "run_python",
        "description": (
            "Execute a read-only Python snippet against the materialized scenario "
            "and return its stdout. Use this to inspect the data (distributions of "
            "step durations, station load, due-date tightness, etc.) before "
            "proposing a heuristic.\n\n"
            "ALREADY IN SCOPE — do not import or rebuild these:\n"
            "  orders          list[Order], fresh / nothing placed yet\n"
            "  kitchen         dict[str, int] — station capacities\n"
            "  state           State (the same one a heuristic would see)\n"
            "  earliest_start  the helper from problem_definition.model\n"
            "Step/Dish/Order/State/Station: just walk `orders`; you do NOT need\n"
            "to import them. Do NOT import `placer`, `discovery.*`, or anything\n"
            "from this repo — the scenario is already built for you.\n\n"
            "From the stdlib you may import freely (collections, statistics, math, ...).\n"
            "Print what you want to see — return values are ignored."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source to exec."},
            },
            "required": ["code"],
        },
    },
}


def _run_python(code: str, scenario: Scenario) -> str:
    state = init_state(scenario.orders, scenario.kitchen)
    ns: dict = {
        "orders":         state.orders,
        "kitchen":        scenario.kitchen,
        "state":          state,
        "earliest_start": earliest_start,
    }
    buf = io.StringIO()
    try:
        with time_limit(EXEC_TIMEOUT_S), redirect_stdout(buf):
            exec(compile(code, "<run_python>", "exec"), ns)
    except Exception as exc:
        buf.write(f"\n{type(exc).__name__}: {exc}")
    out = buf.getvalue()
    if len(out) > OUTPUT_LIMIT:
        out = out[:OUTPUT_LIMIT] + f"\n... [truncated, {len(out) - OUTPUT_LIMIT} more chars]"
    return out or "(no output)"


def _tc_to_dict(tc) -> dict:
    if hasattr(tc, "model_dump"): return tc.model_dump()
    if isinstance(tc, dict):      return tc
    return {
        "id": tc.id,
        "type": tc.type,
        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
    }


def chat_with_tools(
    client:     InferenceClient,
    history:    list[dict],
    scenario:   Scenario,
    max_tokens: int,
) -> str:
    """Send `history` to the model with the `run_python` tool available.
    Dispatch any tool calls and feed results back, until the model returns
    a normal message. Return that message's content; append everything to
    `history` so the caller sees the full transcript."""
    for _ in range(MAX_TOOL_CALLS_PER_TURN + 1):
        resp = client.chat_completion(
            messages   = history,
            tools      = [RUN_PYTHON],
            max_tokens = max_tokens,
        )
        msg   = resp.choices[0].message
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:
            content = msg.content or ""
            history.append({"role": "assistant", "content": content})
            return content
        history.append({
            "role":       "assistant",
            "content":    msg.content or "",
            "tool_calls": [_tc_to_dict(tc) for tc in calls],
        })
        for tc in calls:
            d    = _tc_to_dict(tc)
            fn   = d["function"]
            args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
            code = args.get("code", "")
            print(f"--- run_python ---\n{code}")
            result = _run_python(code, scenario)
            print(f"--- result ---\n{result}")
            history.append({
                "role":         "tool",
                "tool_call_id": d["id"],
                "content":      result,
            })
    raise RuntimeError(f"exceeded {MAX_TOOL_CALLS_PER_TURN} tool calls without a final reply")
