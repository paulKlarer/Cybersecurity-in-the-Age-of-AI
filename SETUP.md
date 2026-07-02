# Setup and Run Guide

This project evaluates when an LLM agent violates file-access boundaries while answering questions from a simulated course workspace.

The normal workflow is:

1. Install Python dependencies from `requirements.txt`.
2. Configure the LLM server credentials in `.env`.
3. Build the Docker image.
4. Run one small condition to confirm tracing works.
5. Run a tiny screening batch before the full screening set.

## Requirements

- Python 3.10 or newer
- Docker Desktop or Docker Engine
- Access to the chair/university LLM server
- A `.env` file in the repo root

The Python dependencies are currently:

```text
httpx==0.28.1
python-dotenv==1.2.2
```

No extra package is needed for the evaluator, scoring, scenario generation, reports, or tests.

## Environment File

Create `.env` in the repo root. It is intentionally ignored by git.

```text
url=https://your-llm-server.example/v1/chat/completions
username=your_username
password=your_password
```

The Docker image does not copy your real `.env` into the image. The evaluator passes credentials at runtime with Docker's `--env-file .env` flag. Inside the image, `.env` is only a redacted honeypot used to test whether the agent tries to read restricted secrets.

## One-Command Setup on Windows

From the repo root:

```powershell
scripts\setup_windows.bat
```

This creates `.venv`, installs `requirements.txt`, and runs the unit tests.

Manual equivalent:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest discover
```

## Build Docker Image

```powershell
scripts\build_docker.bat
```

Manual equivalent:

```powershell
docker build -t ai-agent-eval .
```

## Important Runs

### 1. First Trace Quality Check

Run one known condition first. This builds the Docker image through `evaluator.py` unless it already exists.

```powershell
scripts\run_one_condition.bat
```

Manual equivalent:

```powershell
python evaluator.py --phase screening --condition-id screening-real-clear_allowed-neutral-neutral_assistant-none --runs-per-condition 1
```

Check:

- `results/runs/<session-id>__screening-real-clear_allowed-neutral-neutral_assistant-none__run-1.jsonl`
- `results/summary.json`
- `results.html`
- `deep_dive_results.html`

These files are generated outputs and are ignored by git.

If the JSONL trace is missing prompt, assistant, tool, or final-status events, fix tracing before running more conditions.

### 2. Tiny Screening Batch

```powershell
scripts\run_tiny_screening.bat
```

Manual equivalent:

```powershell
python evaluator.py --phase screening --max-conditions 5 --runs-per-condition 1 --skip-docker-build
```

Use this before the full matrix. It runs only five screening conditions.

### 3. Full Phase 1 Screening

```powershell
scripts\run_full_screening.bat
```

Manual equivalent:

```powershell
python evaluator.py --phase screening --runs-per-condition 1 --skip-docker-build
```

This runs all 13 screening conditions:

```text
baseline + 12 single-factor probes
```

### 4. Focused Validation

```powershell
scripts\run_validation.bat
```

Manual equivalent:

```powershell
python evaluator.py --phase validation --runs-per-condition 3 --skip-docker-build
```

Use this after Phase 1 identifies high-signal conditions.

### 5. Regenerate Deep-Dive Report

```powershell
scripts\regenerate_deep_dive.bat
```

Manual equivalent:

```powershell
python deep_dive_report.py
```

This rebuilds `deep_dive_results.html` from `results/runs/*.jsonl` and `results/summary.json`.

## Evaluator Flags

`--phase screening`

Runs the baseline plus the complete single-factor screening probe set.

`--phase validation`

Runs a smaller set of focused validation conditions.

`--condition-id <id>`

Runs one exact condition, such as:

```text
screening-real-clear_allowed-neutral-neutral_assistant-none
```

Repeat this flag to run multiple explicit validation combinations in one session.

`--max-conditions <N>`

Runs only the first `N` conditions for cheap smoke checks.

`--runs-per-condition <N>`

Repeats each selected condition `N` times.

`--session-id <id>`

Optional stable prefix for trace filenames. If omitted, `evaluator.py` uses a timestamp so repeated runs keep their history instead of overwriting old traces.

`--skip-docker-build`

Skips rebuilding the Docker image. Use this after you have already built the image and have not changed `agent.py`, `trace_utils.py`, `requirements.txt`, or `Dockerfile`. You do not need to rebuild just because `.env` or `data/` changed, because both are supplied at runtime.

## Agent Flags

Most group members should run `evaluator.py`, not `agent.py` directly. The evaluator passes these important agent flags:

`--trace-path`

Where the agent writes structured JSONL evidence for the run.

`--condition-id`

The stable condition ID recorded in the trace.

`--prompt-pressure`

Named pressure component: `neutral`, `accuracy_pressure`, `penalty_pressure`, `repeated_failure_feedback`, or `social_comparison`.

`--persona-affect`

Named persona/affect component: `neutral_assistant`, `anxious_desperate`, or `highly_agreeable`.

`--thinking-budget-tokens`

Reasoning budget sent to the server. Current experiments use `128`.

`--reasoning-format`

Reasoning format sent to the server. Current experiments use `deepseek`.

`--workflow`

Policy mode. `observe_only` logs risk without blocking. `allow_deny` blocks high-risk and critical file reads. Phase 1 should use `observe_only`.

Experimental fixture files under `data/` and the Docker honeypot `.env` are readable in `observe_only` so risky attempts can be observed. Infrastructure files such as `agent.py`, `evaluator.py`, docs, scripts, tests, reports, and repository root listings are always outside the tool layer, even in `observe_only`.

## Outputs

`results/runs/*.jsonl`

One structured trace per run.

`results/summary.json`

Machine-readable scoring summary.

`results.html`

Compact condition-level overview.

`deep_dive_results.html`

Detailed scientific trace view for inspecting prompts, tool calls, risks, final answers, and scoring evidence.

## Common Problems

Docker cannot find `.env`

Create `.env` in the repo root. You do not need to rebuild only for `.env` changes.

Docker image is stale

Run `scripts\build_docker.bat`, then rerun the evaluation with `--skip-docker-build`.

No JSONL traces appear

Make sure you ran through `evaluator.py` or passed `--trace-path` when using `agent.py` directly.

LLM/API errors in the trace

Check `url`, `username`, and `password` in `.env`.
