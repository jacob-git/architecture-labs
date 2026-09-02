"""ADP-001 Phase B2: harder cache task across five AI development patterns."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .b2_evaluator import EvaluationResult, evaluate

API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.6-luna"
RUNNER_VERSION = "adp-phase-b2-runner-v1"
TREATMENTS = ("vibe", "intent", "spec", "context", "agentic")
DEFAULT_OUTPUT = Path("labs/adp_001/results/phase-b2-latest.json")
MAX_AGENTIC_REPAIRS = 3

COMMON_SYSTEM = """You are participating in a controlled software engineering experiment.
Work only from material supplied in the request. Never request or infer hidden evaluator tests.
Return JSON only with exactly these keys:
- implementation: complete Python source for one candidate module
- tests: optional Python test source, or an empty string
- summary: concise explanation

The candidate module must expose:
    class CachedApi
with constructor:
    CachedApi(clock, ttl_seconds=30, max_entries=4)
and methods:
    put_item(client_id, key, value)
    get_item(client_id, key)
Import baseline types with:
    from labs.adp_001.b2_baseline import Response, TinyApi
Do not use third party runtime libraries.
Do not use Markdown fences."""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _repo_state() -> dict[str, Any]:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], check=True, capture_output=True, text=True).stdout.strip())
        return {"commit": commit, "dirty": dirty}
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def _output_text(body: dict[str, Any]) -> str:
    parts: list[str] = []
    for item in body.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])
    return "\n".join(parts).strip()


def _call_model(*, api_key: str, model: str, user_prompt: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "reasoning": {"effort": "none"},
        "input": [
            {"role": "system", "content": COMMON_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail).get("error", {}).get("message", detail)
        except json.JSONDecodeError:
            pass
        raise RuntimeError(f"OpenAI {exc.code}: {detail}") from exc
    text = _output_text(body)
    response_id = body.get("id")
    return {
        "text": text,
        "latencyMs": round((time.perf_counter() - started) * 1000),
        "usage": body.get("usage") or {},
        "responseModel": body.get("model"),
        "responseIdHash": hashlib.sha256(response_id.encode("utf-8")).hexdigest()[:16] if response_id else None,
    }


def _parse_json(text: str) -> dict[str, str]:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("model response JSON must be an object")
    implementation = value.get("implementation")
    if not isinstance(implementation, str) or not implementation.strip():
        raise ValueError("model response must contain non-empty implementation")
    tests = value.get("tests", "")
    summary = value.get("summary", "")
    return {
        "implementation": implementation.strip() + "\n",
        "tests": tests if isinstance(tests, str) else "",
        "summary": summary if isinstance(summary, str) else "",
    }


def _treatment_prompt(root: Path, treatment: str) -> str:
    prompt = _read(root / "b2_prompts" / f"{treatment}.md")
    baseline = _read(root / "b2_baseline.py")
    sections = [
        f"# Development treatment\n{treatment}",
        f"# Treatment instructions\n{prompt}",
        f"# Starting baseline\n```python\n{baseline}\n```",
    ]
    if treatment == "context":
        sections.append(f"# Intent document\n{_read(root / 'b2_prompts' / 'intent.md')}")
    if treatment in {"context", "agentic"}:
        for name in ("ARCHITECTURE.md", "ENGINEERING_RULES.md", "AGENTS.md"):
            sections.append(f"# {name}\n{_read(root / 'b2_context' / name)}")
    if treatment == "agentic":
        sections.append(f"# Feature specification\n{_read(root / 'b2_prompts' / 'spec.md')}")
        sections.append("You may repair your implementation after visible test feedback. Hidden tests will never be shown.")
    return "\n\n".join(sections)


def _visible_feedback(evaluation: EvaluationResult) -> str:
    visible = next(check for check in evaluation.checks if check.name == "b2_tests_visible.py")
    dependency = next(check for check in evaluation.checks if check.name == "dependency_policy")
    return (
        f"Visible tests: {'PASS' if visible.passed else 'FAIL'}\n{visible.detail}\n\n"
        f"Dependency policy: {'PASS' if dependency.passed else 'FAIL'}\n{dependency.detail}"
    )


def _write_candidate(run_dir: Path, parsed: dict[str, str], attempt: int) -> Path:
    candidate = run_dir / f"candidate-attempt-{attempt}.py"
    candidate.write_text(parsed["implementation"], encoding="utf-8")
    (run_dir / f"generated-tests-attempt-{attempt}.py").write_text(parsed["tests"], encoding="utf-8")
    (run_dir / f"summary-attempt-{attempt}.txt").write_text(parsed["summary"] + "\n", encoding="utf-8")
    return candidate


def _run_one(*, root: Path, treatment: str, trial: int, api_key: str, model: str) -> dict[str, Any]:
    run_dir = root / "results" / "b2-runs" / f"{treatment}-{trial:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    base_prompt = _treatment_prompt(root, treatment)
    prompt = base_prompt
    calls: list[dict[str, Any]] = []
    interactions = 0
    repairs = 0
    candidate: Path | None = None
    parsed: dict[str, str] | None = None
    evaluation: EvaluationResult | None = None
    max_attempts = 1 + (MAX_AGENTIC_REPAIRS if treatment == "agentic" else 0)

    for attempt in range(1, max_attempts + 1):
        result = _call_model(api_key=api_key, model=model, user_prompt=prompt)
        interactions += 1
        parsed = _parse_json(result["text"])
        candidate = _write_candidate(run_dir, parsed, attempt)
        evaluation = evaluate(candidate, treatment)
        calls.append({
            "attempt": attempt,
            "latencyMs": result["latencyMs"],
            "usage": result["usage"],
            "responseModel": result["responseModel"],
            "responseIdHash": result["responseIdHash"],
            "candidateDigest": _digest_text(parsed["implementation"]),
            "generatedTestsBytes": len(parsed["tests"].encode("utf-8")),
        })
        visible = next(check for check in evaluation.checks if check.name == "b2_tests_visible.py")
        dependency = next(check for check in evaluation.checks if check.name == "dependency_policy")
        if treatment != "agentic" or (visible.passed and dependency.passed):
            break
        if attempt < max_attempts:
            repairs += 1
            prompt = "\n\n".join([
                base_prompt,
                "# Current implementation",
                f"```python\n{parsed['implementation']}\n```",
                "# Visible validation feedback",
                _visible_feedback(evaluation),
                "Repair the implementation autonomously. Return the same JSON structure with the complete corrected implementation.",
            ])

    assert candidate is not None and parsed is not None and evaluation is not None
    return {
        "treatment": treatment,
        "trial": trial,
        "modelAlias": model,
        "calls": calls,
        "modelInteractions": interactions,
        "repairAttempts": repairs,
        "evaluation": evaluation.to_dict(),
        "finalCandidate": str(candidate.relative_to(root)),
        "summary": parsed["summary"],
    }


def _summarize(records: list[dict[str, Any]], *, model: str, repeats: int, root: Path) -> dict[str, Any]:
    usage = Counter()
    latencies: list[int] = []
    for record in records:
        for call in record.get("calls", []):
            latencies.append(call["latencyMs"])
            for key, value in (call.get("usage") or {}).items():
                if isinstance(value, (int, float)):
                    usage[key] += value
    by_treatment: dict[str, Any] = {}
    for treatment in TREATMENTS:
        rows = [record for record in records if record.get("treatment") == treatment and "error" not in record]
        by_treatment[treatment] = {
            "completed": len(rows),
            "fullPasses": sum(row["evaluation"]["passed"] == row["evaluation"]["total"] for row in rows),
            "meanScore": round(sum(row["evaluation"]["score"] for row in rows) / len(rows), 4) if rows else None,
            "meanModelInteractions": round(sum(row["modelInteractions"] for row in rows) / len(rows), 2) if rows else None,
            "meanRepairAttempts": round(sum(row["repairAttempts"] for row in rows) / len(rows), 2) if rows else None,
        }
    repo = _repo_state()
    prompt_material = "\n".join(_treatment_prompt(root, treatment) for treatment in TREATMENTS)
    return {
        "lab": "ADP-001",
        "phase": "B2 — constraint-dense cache comparison",
        "runnerVersion": RUNNER_VERSION,
        "repositoryCommit": repo["commit"],
        "repositoryDirty": repo["dirty"],
        "modelAlias": model,
        "treatments": list(TREATMENTS),
        "repeats": repeats,
        "trialsStarted": len(records),
        "completed": sum("error" not in record for record in records),
        "errors": sum("error" in record for record in records),
        "promptDigest": _digest_text(prompt_material),
        "baselineDigest": _digest_text(_read(root / "b2_baseline.py")),
        "hiddenTestsDigest": _digest_text(_read(root / "b2_tests_hidden.py")),
        "byTreatment": by_treatment,
        "latencyMsTotal": sum(latencies),
        "usage": dict(usage),
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required for ADP-001 Phase B2.", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parent
    model = os.environ.get("ADP_LAB_MODEL", DEFAULT_MODEL)
    try:
        repeats = int(os.environ.get("ADP_LAB_REPEATS", "1"))
        if repeats < 1:
            raise ValueError
    except ValueError:
        print("ADP_LAB_REPEATS must be an integer >= 1", file=sys.stderr)
        return 2
    selected_raw = os.environ.get("ADP_LAB_TREATMENTS", ",".join(TREATMENTS))
    selected = tuple(item.strip() for item in selected_raw.split(",") if item.strip())
    unknown = [item for item in selected if item not in TREATMENTS]
    if unknown:
        print(f"Unknown treatment(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    output = Path(os.environ.get("ADP_B2_OUTPUT", DEFAULT_OUTPUT))
    records: list[dict[str, Any]] = []
    total = len(selected) * repeats
    print(f"ADP-001 Phase B2: {len(selected)} treatment(s) x {repeats} repeat(s) = {total} trial(s) using {model}")
    position = 0
    for trial in range(1, repeats + 1):
        for treatment in selected:
            position += 1
            print(f"[{position}/{total}] {treatment} trial {trial}")
            try:
                record = _run_one(root=root, treatment=treatment, trial=trial, api_key=api_key, model=model)
                records.append(record)
                evaluation = record["evaluation"]
                print(f"  score={evaluation['score']:.4f} interactions={record['modelInteractions']} repairs={record['repairAttempts']}")
            except Exception as exc:
                records.append({"treatment": treatment, "trial": trial, "error": f"{type(exc).__name__}: {exc}"})
                print(f"  ERROR: {exc}", file=sys.stderr)
    summary = _summarize(records, model=model, repeats=repeats, root=root)
    payload = {"summary": summary, "records": records}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"result={output}")
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
