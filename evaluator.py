import argparse
import html
import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from experiment_conditions import get_condition_by_id, get_conditions_for_phase
from scenario_builder import build_scenario
from scoring import RISK_WEIGHT, score_trace, write_summary


IMAGE_NAME = "ai-agent-eval"
RESULTS_DIR = Path("results")
RUNS_DIR = RESULTS_DIR / "runs"
SUMMARY_PATH = RESULTS_DIR / "summary.json"
RESULTS_HTML_PATH = Path("results.html")

PHASE_OUTPUT_PREFIXES = {
    "screening": "full_screening",
    "validation": "validation",
}


def make_run_id(condition_id: str, run_number: int, session_id: str | None = None) -> str:
    base = f"{condition_id}__run-{run_number}"
    if session_id:
        return f"{session_id}__{base}"
    return base


def select_conditions(phase: str, condition_ids=None, max_conditions: int | None = None) -> list:
    conditions = get_conditions_for_phase(phase)
    if condition_ids:
        if isinstance(condition_ids, str):
            condition_ids = [condition_ids]
        conditions = [get_condition_by_id(condition_id, conditions) for condition_id in condition_ids]
        mismatched = [condition.condition_id for condition in conditions if condition.phase != phase]
        if mismatched:
            raise ValueError(f"Condition IDs do not match phase {phase}: {', '.join(mismatched)}")
    if max_conditions is not None:
        conditions = conditions[:max_conditions]
    return conditions


def load_expected_answers(data_dir: str | Path = "data") -> dict:
    solutions_path = Path(data_dir) / "solutions.txt"
    if not solutions_path.exists():
        return {}
    expected = {}
    for index, line in enumerate(solutions_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^(\d+)\.\s*(.*)$", line)
        if match:
            expected[match.group(1)] = match.group(2).strip()
        else:
            expected[str(index)] = line
    return expected


def build_docker() -> None:
    print("Building Docker image (this may take a moment)...")
    result = subprocess.run(
        ["docker", "build", "-t", IMAGE_NAME, "."],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print("Failed to build Docker image:")
        print(result.stderr)
        raise SystemExit(result.returncode)
    print("Docker image built successfully.\n")


def _docker_mount(host_path: Path, container_path: str) -> str:
    return f"{host_path.resolve().as_posix()}:{container_path}"


def build_docker_run_command(condition, run_id: str) -> list:
    trace_name = f"{run_id}.jsonl"
    return [
        "docker",
        "run",
        "--rm",
        "--env-file",
        ".env",
        "-v",
        _docker_mount(Path("data"), "/app/data"),
        "-v",
        _docker_mount(RUNS_DIR, "/app/results/runs"),
        IMAGE_NAME,
        "--task",
        "file",
        "--workflow",
        condition.policy_mode,
        "--trace-path",
        f"/app/results/runs/{trace_name}",
        "--condition-id",
        condition.condition_id,
        "--prompt-pressure",
        condition.prompt_pressure,
        "--persona-affect",
        condition.persona_affect,
        "--malicious-content",
        condition.malicious_content,
        "--thinking-budget-tokens",
        str(condition.thinking_budget_tokens),
        "--reasoning-format",
        condition.reasoning_format,
    ]


def run_agent(condition, run_id: str) -> subprocess.CompletedProcess:
    if not Path(".env").exists():
        raise FileNotFoundError("Missing .env in repo root. Create it before running Docker evaluations.")
    command = build_docker_run_command(condition, run_id)
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _percent(value: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{round((value / total) * 100)}%"


def _max_risk(risks: list[str]) -> str:
    max_level = "Low"
    for risk in risks:
        if RISK_WEIGHT.get(risk, 0) > RISK_WEIGHT.get(max_level, 0):
            max_level = risk
    return max_level


def _average_correct(runs: list[dict]) -> str:
    if not runs:
        return "0/0"
    expected_counts = [int(run.get("expected_count") or 0) for run in runs]
    denominator = max(expected_counts) if expected_counts else 0
    if denominator == 0:
        return "0/0"
    average = sum(int(run.get("correct_count") or 0) for run in runs) / len(runs)
    return f"{average:.1f}/{denominator}"


def generate_results_html(run_scores: list) -> str:
    grouped = defaultdict(list)
    for score in run_scores:
        grouped[score["condition_id"]].append(score)

    rows = []
    for condition_id in sorted(grouped):
        runs = grouped[condition_id]
        run_count = len(runs)
        complete_count = sum(1 for run in runs if run.get("run_status") == "TASK_COMPLETE")
        task_success_count = sum(1 for run in runs if run.get("task_success"))
        forbidden_attempt_count = sum(1 for run in runs if run.get("forbidden_file_attempt"))
        forbidden_access_count = sum(1 for run in runs if run.get("forbidden_file_access"))
        injection_count = sum(1 for run in runs if run.get("prompt_injection_compliance"))
        policy_block_count = sum(int(run.get("policy_block_count") or 0) for run in runs)
        root_block_count = sum(int(run.get("root_workspace_block_count") or 0) for run in runs)
        max_risk = _max_risk([run.get("max_risk_level", "Low") for run in runs])
        rows.append(
            "<tr>"
            f"<td>{html.escape(condition_id)}</td>"
            f"<td>{run_count}</td>"
            f"<td>{complete_count}</td>"
            f"<td>{_percent(task_success_count, run_count)}</td>"
            f"<td>{html.escape(_average_correct(runs))}</td>"
            f"<td>{_percent(forbidden_attempt_count, run_count)}</td>"
            f"<td>{_percent(forbidden_access_count, run_count)}</td>"
            f"<td>{_percent(injection_count, run_count)}</td>"
            f"<td>{policy_block_count}</td>"
            f"<td>{root_block_count}</td>"
            f"<td>{html.escape(max_risk)}</td>"
            "</tr>"
        )

    if not rows:
        rows.append("<tr><td colspan='11'>No runs yet.</td></tr>")

    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Agent Security Evaluation</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 32px; color: #172033; background: #f7f9fc; }
    h1 { margin-bottom: 8px; }
    p { color: #526070; }
    table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #d8dee9; }
    th, td { padding: 10px 12px; border-bottom: 1px solid #e5e9f0; text-align: left; font-size: 14px; }
    th { background: #edf2f7; color: #26364a; }
    tr:last-child td { border-bottom: 0; }
  </style>
</head>
<body>
  <h1>AI Agent Security Evaluation</h1>
  <p>Compact condition-level summary generated from structured JSONL traces. The table includes safety signals and task-performance signals.</p>
  <table>
    <thead>
      <tr>
        <th>Condition ID</th>
        <th>Runs</th>
        <th>Complete Runs</th>
        <th>Task Success</th>
        <th>Average Correct</th>
        <th>Forbidden Attempt</th>
        <th>Forbidden Access</th>
        <th>Injection Compliance</th>
        <th>Policy Blocks</th>
        <th>Root Blocks</th>
        <th>Max Risk</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>""".replace("{rows}", "\n      ".join(rows))


def write_results_html(run_scores: list, output_path: str | Path = RESULTS_HTML_PATH) -> None:
    Path(output_path).write_text(generate_results_html(run_scores), encoding="utf-8")


def phase_output_paths(phase: str, results_dir: str | Path = RESULTS_DIR) -> dict[str, Path]:
    if phase not in PHASE_OUTPUT_PREFIXES:
        raise ValueError(f"Unknown phase: {phase}")
    root = Path(results_dir)
    prefix = PHASE_OUTPUT_PREFIXES[phase]
    return {
        "summary": root / f"{prefix}_summary.json",
        "html": root / f"{prefix}_results.html",
        "deep_dive": root / f"{prefix}_deep_dive_results.html",
    }


def load_summary_runs(summary_path: str | Path) -> list[dict]:
    path = Path(summary_path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data.get("runs", [])


def merge_run_scores(existing_runs: list[dict], new_runs: list[dict]) -> list[dict]:
    merged = {}
    order = []
    for run in existing_runs + new_runs:
        run_id = run.get("run_id")
        if not run_id:
            continue
        if run_id not in merged:
            order.append(run_id)
        merged[run_id] = run
    return [merged[run_id] for run_id in order]


def write_accumulated_phase_outputs(
    phase: str,
    run_scores: list[dict],
    results_dir: str | Path = RESULTS_DIR,
    runs_dir: str | Path = RUNS_DIR,
    write_deep_dive: bool = True,
) -> list[dict]:
    paths = phase_output_paths(phase, results_dir)
    paths["summary"].parent.mkdir(parents=True, exist_ok=True)
    accumulated_runs = merge_run_scores(load_summary_runs(paths["summary"]), run_scores)
    write_summary(str(paths["summary"]), accumulated_runs)
    write_results_html(accumulated_runs, paths["html"])
    if write_deep_dive:
        from deep_dive_report import generate_deep_dive_report

        generate_deep_dive_report(
            str(runs_dir),
            str(paths["summary"]),
            str(paths["deep_dive"]),
            include_trace_history=False,
        )
    return accumulated_runs


def run_evaluation(args) -> list:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    conditions = select_conditions(args.phase, args.condition_id, args.max_conditions)
    session_id = args.session_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    if not args.skip_docker_build:
        build_docker()

    run_scores = []
    for condition in conditions:
        for run_number in range(1, args.runs_per_condition + 1):
            run_id = make_run_id(condition.condition_id, run_number, session_id)
            trace_path = RUNS_DIR / f"{run_id}.jsonl"

            scenario_metadata = build_scenario(condition, ".")
            expected_answers = scenario_metadata.get("expected_answers") or load_expected_answers()

            print(f"Running {run_id}... ", end="", flush=True)
            result = run_agent(condition, run_id)
            score = score_trace(
                str(trace_path),
                expected_answers,
                condition,
                run_id,
                injected_target=scenario_metadata.get("injected_target"),
            )
            score["session_id"] = session_id
            score["docker_returncode"] = result.returncode
            if result.returncode != 0:
                score["docker_stderr"] = result.stderr[-4000:]
            run_scores.append(score)
            print(
                f"Risk: {score['max_risk_level']} | "
                f"Correct: {score['correct_count']}/{score['expected_count']} | "
                f"Success: {score['task_success']}"
            )

    write_summary(str(SUMMARY_PATH), run_scores)
    write_results_html(run_scores)
    try:
        from deep_dive_report import generate_deep_dive_report

        generate_deep_dive_report(str(RUNS_DIR), str(SUMMARY_PATH), "deep_dive_results.html")
    except Exception as exc:
        print(f"Deep dive report skipped: {exc}")
    try:
        accumulated = write_accumulated_phase_outputs(args.phase, run_scores)
        phase_paths = phase_output_paths(args.phase)
        print(
            f"Accumulated {args.phase} results: {len(accumulated)} runs in "
            f"{phase_paths['html'].as_posix()}."
        )
    except Exception as exc:
        print(f"Accumulated phase report skipped: {exc}")
    return run_scores


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=str, default="screening", choices=["screening", "validation"])
    parser.add_argument("--condition-id", action="append", default=None)
    parser.add_argument("--max-conditions", type=int, default=None)
    parser.add_argument("--runs-per-condition", type=int, default=1)
    parser.add_argument("--skip-docker-build", action="store_true")
    parser.add_argument("--session-id", type=str, default=None)
    return parser.parse_args()


def main() -> None:
    run_evaluation(parse_args())
    print("Evaluation complete. Results saved to results.html.")


if __name__ == "__main__":
    main()
