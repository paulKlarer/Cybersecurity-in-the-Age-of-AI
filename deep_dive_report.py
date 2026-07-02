import argparse
import html
import json
from pathlib import Path

from trace_utils import read_trace_events


def _load_summary(summary_path: str | Path) -> list:
    path = Path(summary_path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data.get("runs", [])


def _summary_runs_with_trace_history(runs_dir: Path, summary_runs: list) -> list:
    by_run_id = {run.get("run_id"): dict(run) for run in summary_runs if run.get("run_id")}
    for trace_path in sorted(runs_dir.glob("*.jsonl")):
        run_id = trace_path.stem
        if run_id in by_run_id:
            by_run_id[run_id].setdefault("trace_path", trace_path.as_posix())
            continue
        events = read_trace_events(str(trace_path))
        started = next((event for event in events if event.get("event") == "run_started"), {})
        finished = next((event for event in reversed(events) if event.get("event") == "run_finished"), {})
        by_run_id[run_id] = {
            "run_id": run_id,
            "condition_id": started.get("condition_id", "unknown"),
            "trace_path": trace_path.as_posix(),
            "task_success": finished.get("status") == "TASK_COMPLETE",
            "max_risk_level": _max_risk_from_events(events),
            "summary_source": "trace_only",
        }
    return list(by_run_id.values())


def _max_risk_from_events(events: list) -> str:
    weights = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    max_risk = "Low"
    for event in events:
        risk = event.get("risk_level")
        if weights.get(risk, 0) > weights.get(max_risk, 0):
            max_risk = risk
    return max_risk


def _event_text(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False)
    return str(value)


def _pre(value) -> str:
    return f"<pre>{html.escape(_event_text(value))}</pre>"


def _trace_path_for_run(runs_dir: Path, run: dict) -> Path:
    trace_path = run.get("trace_path")
    if trace_path:
        path = Path(trace_path)
        if path.exists():
            return path
    return runs_dir / f"{run.get('run_id', 'unknown')}.jsonl"


def _render_run(run: dict, events: list) -> str:
    prompts = [event for event in events if event.get("event") == "prompt_sent"]
    assistant_events = [
        event for event in events
        if event.get("event") in {"assistant_response", "assistant_reasoning"}
    ]
    tool_events = [
        event for event in events
        if event.get("event") in {"tool_call_requested", "tool_call_completed"}
    ]
    final_events = [event for event in events if event.get("event") == "final_answer"]

    tool_rows = []
    for event in tool_events:
        tool_rows.append(
            "<tr>"
            f"<td>{html.escape(str(event.get('step', '')))}</td>"
            f"<td>{html.escape(event.get('event', ''))}</td>"
            f"<td>{html.escape(event.get('tool', ''))}</td>"
            f"<td>{html.escape(event.get('normalized_path', ''))}</td>"
            f"<td>{html.escape(event.get('path_category', ''))}</td>"
            f"<td>{html.escape(str(event.get('access_granted', '')))}</td>"
            f"<td>{html.escape(event.get('risk_level', ''))}</td>"
            "</tr>"
        )
    if not tool_rows:
        tool_rows.append("<tr><td colspan='7'>No tool calls recorded.</td></tr>")

    prompt_html = "".join(_pre(prompt) for prompt in prompts) or "<p>No prompt event recorded.</p>"
    assistant_html = "".join(_pre(event) for event in assistant_events) or "<p>No assistant responses recorded.</p>"
    final_html = "".join(_pre(event) for event in final_events) or "<p>No final answer recorded.</p>"
    raw_html = _pre(events)

    run_id = html.escape(run.get('run_id', 'unknown'))
    return f"""
<article class="run" id="run-{run_id}" data-run-id="{run_id}" data-condition-id="{html.escape(run.get('condition_id', 'unknown'))}" data-risk="{html.escape(run.get('max_risk_level', 'Low'))}" data-success="{html.escape(str(run.get('task_success', False)).lower())}">
<details open>
  <summary>
    <strong>{run_id}</strong>
    <span>{html.escape(run.get('condition_id', 'unknown'))}</span>
    <span>Success: {html.escape(str(run.get('task_success', False)))}</span>
    <span>Risk: {html.escape(run.get('max_risk_level', 'Low'))}</span>
  </summary>
  <section>
    <details><summary>Condition</summary>{_pre(run.get('condition', {'condition_id': run.get('condition_id')}))}</details>
    <details><summary>Prompts</summary>{prompt_html}</details>
    <details><summary>Assistant Sequence</summary>{assistant_html}</details>
    <details open><summary>Tool Calls</summary>
      <table>
        <thead>
          <tr><th>Step</th><th>Event</th><th>Tool</th><th>Path</th><th>Category</th><th>Granted</th><th>Risk</th></tr>
        </thead>
        <tbody>{''.join(tool_rows)}</tbody>
      </table>
    </details>
    <details open><summary>Final Answer</summary>{final_html}</details>
    <details><summary>Scoring</summary>{_pre(run)}</details>
    <details><summary>Raw Trace</summary>{raw_html}</details>
  </section>
</details>
</article>
"""


def generate_deep_dive_report(
    runs_dir: str | Path = "results/runs",
    summary_path: str | Path = "results/summary.json",
    output_path: str | Path = "deep_dive_results.html",
    include_trace_history: bool = True,
) -> None:
    runs_dir = Path(runs_dir)
    summary_runs = _load_summary(summary_path)
    if include_trace_history:
        runs = _summary_runs_with_trace_history(runs_dir, summary_runs)
    else:
        runs = summary_runs
    sections = []
    options = []
    for run in runs:
        trace_path = _trace_path_for_run(runs_dir, run)
        events = read_trace_events(str(trace_path))
        sections.append(_render_run(run, events))
        label = f"{run.get('run_id', 'unknown')} | {run.get('condition_id', 'unknown')} | risk {run.get('max_risk_level', 'Low')}"
        options.append(f"<option value=\"{html.escape(run.get('run_id', 'unknown'))}\">{html.escape(label)}</option>")

    if not sections:
        sections.append("<p>No runs found. Run evaluator.py first.</p>")

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Deep Dive Results</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #172033; background: #f7f9fc; }}
    h1 {{ margin-bottom: 8px; }}
    .toolbar {{ position: sticky; top: 0; background: #f7f9fc; border-bottom: 1px solid #d8dee9; padding: 12px 0; margin-bottom: 16px; }}
    .toolbar label {{ font-weight: 700; margin-right: 8px; }}
    select, input {{ padding: 6px 8px; border: 1px solid #aeb8c6; border-radius: 4px; min-width: 260px; }}
    .run {{ background: white; border: 1px solid #d8dee9; margin-bottom: 16px; padding: 12px; }}
    summary {{ cursor: pointer; display: flex; gap: 16px; flex-wrap: wrap; }}
    section {{ margin-top: 12px; display: grid; gap: 10px; }}
    pre {{ white-space: pre-wrap; background: #101827; color: #edf2f7; padding: 12px; overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; margin: 8px 0 16px; }}
    th, td {{ padding: 8px; border-bottom: 1px solid #e5e9f0; text-align: left; font-size: 13px; }}
    th {{ background: #edf2f7; }}
  </style>
  <script>
    function filterRuns() {{
      const selected = document.getElementById('runSelector').value;
      const query = document.getElementById('runSearch').value.toLowerCase();
      document.querySelectorAll('.run').forEach((run) => {{
        const matchesSelection = !selected || run.dataset.runId === selected;
        const text = (run.dataset.runId + ' ' + run.dataset.conditionId + ' ' + run.dataset.risk + ' ' + run.dataset.success).toLowerCase();
        const matchesQuery = !query || text.includes(query);
        run.style.display = matchesSelection && matchesQuery ? '' : 'none';
      }});
    }}
  </script>
</head>
<body>
  <h1>Deep Dive Results</h1>
  <p>Scientific trace browser generated from JSONL run evidence.</p>
  <div class="toolbar">
    <label for="runSelector">Run</label>
    <select id="runSelector" onchange="filterRuns()">
      <option value="">All runs</option>
      {''.join(options)}
    </select>
    <label for="runSearch">Search</label>
    <input id="runSearch" oninput="filterRuns()" placeholder="condition, risk, success">
  </div>
  {''.join(sections)}
</body>
</html>"""
    Path(output_path).write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", default="results/runs")
    parser.add_argument("--summary-path", default="results/summary.json")
    parser.add_argument("--output", default="deep_dive_results.html")
    args = parser.parse_args()
    generate_deep_dive_report(args.runs_dir, args.summary_path, args.output)
    print(f"Deep dive report saved to {args.output}.")


if __name__ == "__main__":
    main()
