"""LLM-discovered priority heuristics. One .py file per iteration, plus a row
per iteration appended to runs.csv. Successful iterations expose a
`priority(task, state)` function and are importable like the baselines;
failed iterations are still saved (so students can inspect what went wrong)
and may not be importable.

`save_iteration` is the persistence entry-point called by the discovery loop.
"""

import csv
from datetime import datetime
from pathlib import Path


HERE       = Path(__file__).parent
RUNS_CSV   = HERE / "runs.csv"
CSV_FIELDS = [
    "timestamp", "run_id", "scenario", "model", "iter",
    "total_lateness", "status", "file",
]


def save_iteration(
    run_id:         str,
    scenario:       str,
    model:          str,
    iteration:      int,
    code:           str,
    total_lateness: float | None,
    error:          str   | None,
) -> Path:
    """Save one iteration's code as a .py module and append a summary row
    to runs.csv. Returns the .py path.

    On success: pass `total_lateness=<value>` and `error=None`.
    On failure: pass `total_lateness=None` and `error=<exception class name>`.
    """
    HERE.mkdir(parents=True, exist_ok=True)
    status = "success" if error is None else f"failed:{error}"
    py_path = HERE / f"run_{run_id}_iter{iteration}.py"

    lateness_line = (
        f"  total_lateness: {total_lateness:.1f}\n" if total_lateness is not None else ""
    )
    header = (
        f'"""Discovered priority heuristic.\n\n'
        f'  Run:            {run_id}\n'
        f'  Iteration:      {iteration}\n'
        f'  Scenario:       {scenario}\n'
        f'  Model:          {model}\n'
        f'  Status:         {status}\n'
        f'{lateness_line}'
        f'"""\n\n'
        "from models.for_llm import State, Step, earliest_start  # noqa: F401\n\n\n"
    )
    py_path.write_text(header + code + "\n")

    write_header = not RUNS_CSV.exists()
    with RUNS_CSV.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow({
            "timestamp":      datetime.now().isoformat(timespec="seconds"),
            "run_id":         run_id,
            "scenario":       scenario,
            "model":          model,
            "iter":           iteration,
            "total_lateness": f"{total_lateness:.1f}" if total_lateness is not None else "",
            "status":         status,
            "file":           py_path.name,
        })
    return py_path
