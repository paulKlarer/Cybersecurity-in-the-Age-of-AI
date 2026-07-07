import argparse
import json
from pathlib import Path

from deep_dive_report import generate_deep_dive_report
from evaluator import write_results_html
from trace_utils import read_trace_events


def _resolve_trace_path(summary_path: Path, run: dict) -> Path:
    trace_path = Path(run.get("trace_path") or "")
    if trace_path.exists():
        return trace_path
    if trace_path and (summary_path.parent / trace_path).exists():
        return summary_path.parent / trace_path
    return summary_path.parent / "runs" / f"{run.get('run_id', 'unknown')}.jsonl"


def _trace_run_status(trace_path: Path) -> str:
    events = read_trace_events(str(trace_path))
    finished = next((event for event in reversed(events) if event.get("event") == "run_finished"), None)
    if not finished or not finished.get("status"):
        raise ValueError(f"No run_finished status in {trace_path}")
    return finished["status"]


def backfill_summary_run_statuses(summary_path: str | Path) -> int:
    summary_path = Path(summary_path)
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    changed = 0
    for run in data.get("runs", []):
        if "run_status" in run:
            continue
        run["run_status"] = _trace_run_status(_resolve_trace_path(summary_path, run))
        changed += 1
    if changed:
        summary_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return changed


def backfill_results_dir(results_dir: str | Path = "results") -> dict[str, int]:
    results_dir = Path(results_dir)
    changes = {}
    for summary_path in sorted(results_dir.glob("*_summary.json")):
        changed = backfill_summary_run_statuses(summary_path)
        changes[summary_path.name] = changed
        if changed:
            prefix = summary_path.name.removesuffix("_summary.json")
            deep_dive_path = results_dir / f"{prefix}_deep_dive_results.html"
            runs = json.loads(summary_path.read_text(encoding="utf-8")).get("runs", [])
            write_results_html(runs, results_dir / f"{prefix}_results.html")
            generate_deep_dive_report(
                results_dir / "runs",
                summary_path,
                deep_dive_path,
                include_trace_history=_has_trace_only_history(deep_dive_path),
            )
    return changes


def _has_trace_only_history(deep_dive_path: Path) -> bool:
    return deep_dive_path.exists() and "trace_only" in deep_dive_path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default="results")
    args = parser.parse_args()
    for name, changed in backfill_results_dir(args.results_dir).items():
        print(f"{name}: backfilled {changed} run_status values")


if __name__ == "__main__":
    main()
