"""ADP-001 Phase B: compare five AI development patterns with one model."""

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

from .evaluator import EvaluationResult, evaluate

API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.6-luna"
RUNNER_VERSION = "adp-phase-b-runner-v1"
TREATMENTS = ("vibe", "intent", "spec", "context", "agentic")
DEFAULT_OUTPUT = Path("labs/adp_001/results/phase-b-latest.json")
MAX_AGENTIC_REPAIRS = 3

COMMON_SYSTEM = """You are participating in a controlled software-engineering experiment.
Work only from the material supplied in this request. Never infer or request access to hidden evaluator tests.
Your implementation must be returned as JSON with exactly these keys:
- implementation: complete Python source for one candidate module
- tests: optional Python test source you would add for the feature, or an empty string
- summary: concise explanation of the change

The candidate module is the experiment boundary. It must expose a class named RateLimitedApi with this constructor:
    RateLimitedApi(clock, limit=10, window_seconds=60)
and these methods:
    health(client_id)
    put_item(client_id, key, value)
    get_item(client_id, key)
The methods must return the same Response type used by the baseline module. Import baseline types with:
    from labs.adp_001.baseline import Response, TinyApi
Do not use third-party runtime libraries.
Return JSON only. Do not use Markdown fences."""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"model did not return valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("model response JSON must be an object")
    implementation = value.get("implementation")
    if not isinstance(implementation, str) or not implementation.strip():
        raise ValueError("model response must contain non-empty implementation source")
    tests = value.get("tests", "")
    summary = value.get("summary", "")
    return {
        "implementation": implementation.strip() + "\n",
        "tests": tests if isinstance(tests, str) else "",
        "summary": summary if isinstance(summary, str) else "",
    }


def _treatment_prompt(root: Path, treatment: str) -> str:
    prompt = _read(root / "prompts" / f"{treatment}.md")
    baseline = _read(root / "baseline.py")
    sections = [
        f"# Development treatment\n{treatment}",
        f"# Treatment instructions\n{prompt}",
        f"# Starting baseline\n```python\n{baseline}\n```",
    ]

    if treatment == "context":
        sections.append(f"# Intent document\n{_read(root / 'prompts' / 'intent.md')}")
    if treatment in {"context", "agentic"}:
        sections.extend(
            [
                f"# ARCHITECTURE.md\n{_read(root / 'context' / 'ARCHITECTURE.md')}",
                f"# ENGINEERING_RULES.md\n{_read(root / 'context' / 'ENGINEERING_RULES.md')}",
                f"# AGENTS.md\n{_read(root / 'context' / 'AGENTS.md')}",
            ]
        )
    if treatment == "agentic":
        sections.append(f"# Feature specification\n{_read(root / 'prompts' / 'spec.md')}")
        sections.append("You may autonomously repair your implementation after visible test failures supplied by the harness. Hidden tests will never be shown.")

    return "\n\n".join(sections)


def _visible_feedback(evaluation: EvaluationResult) -> str:
    visible = next((check for check in evaluation.checks if check.name == "tests_visible.py"), None)
    dependency = next((check for check in evaluation.checks if check.name == "dependency_policy"), None)
    parts = []
    if visible:
        parts.append(f"Visible test result: {'PASS' if visible.passed else 'FAIL'}\n{visible.detail}")
    if dependency:
        parts.append(f"Dependency policy: {'PASS' if dependency.passed else 'FAIL'}\n{dependency.detail}")
    return "\n\n".join(parts)


def _write_candidate(run_dir: Path, parsed: dict[str, str], attempt: int) -> Path:
    candidate = run_dir / f"candidate-attempt-{attempt}.py"
    candidate.write_text(parsed["implementation"], encoding="utf-8")
    (run_dir / f"generated-tests-attempt-{attempt}.py").write_text(parsed["tests"], encoding="utf-8")
    (run_dir / f"summary-attempt-{attempt}.txt").write_text(parsed["summary"] + "\n", encoding="utf-8")
    return candidate


def _run_one(*, root: Path, treatment: str, trial: int, api_key: str, model: str) -> dict[str, Any]:
    run_dir = root / "results" / "runs" / f"{treatment}-{trial:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    base_prompt = _treatment_prompt(root, treatment)
    prompt = base_prompt
    interactions = 0
    repair_attempts = 0
    calls: list[dict[str, Any]] = []
    final_evaluation: EvaluationResult | None = None
    parsed: dict[str, str] | None = None
    candidate: Path | None = None

    max_attempts = 1 + (MAX_AGENTIC_REPAIRS if treatment == "agentic" else 0)
    for attempt in range(1, max_attempts + 1):
        model_result = _call_model(api_key=api_key, model=model, user_prompt=prompt)
        interactions += 1
        parsed = _parse_json(model_result["text"])
        candidate = _write_candidate(run_dir, parsed, attempt)
        final_evaluation = evaluate(candidate, mode=treatment)
        calls.append(
            {
                "attempt": attempt,
                "latencyMs": model_result["latencyMs"],
                "usage": model_result["usage"],
                "responseModel": model_result["responseModel"],
                "responseIdHash": model_result["responseIdHash"],
                "candidateDigest": hashlib.sha256(parsed["implementation"].encode("utf-8")).hexdigest(),
                "generatedTestsBytes": len(parsed["tests"].encode("utf-8")),
            }
        )

        visible = next(check for check in final_evaluation.checks if check.name == "tests_visible.py")
        dependency = next(check for check in final_evaluation.checks if check.name == "dependency_policy")
        if treatment != "agentic" or (visible.passed and dependency.passed):
            break
        if attempt < max_attempts:
            repair_attempts += 1
            prompt = "\n\n".join(
                [
                    base_prompt,
                    "# Current implementation",
                    f"```python\n{parsed['implementation']}\n```",
                    "# Visible validation feedback",
                    _visible_feedback(final_evaluation),
                    "Repair the implementation autonomously. Return the same JSON structure with the complete corrected implementation.",
                ]
            )

    assert candidate is not None and parsed is not None and final_evaluation is not None
    eval_dict = final_evaluation.to_dict()
    eval_dict["model_interactions"] = interactions
    eval_dict["repair_attempts"] = repair_attempts

    return {
        "treatment": treatment,
        "trial": trial,
        "modelAlias": model,
        "calls": calls,
        "modelInteractions": interactions,
        "repairAttempts": repair_attempts,
        "evaluation": eval_dict,
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
        if not rows:
            by_treatment[treatment] = {"completed": 0}
            continue
        by_treatment[treatment] = {
            "completed": len(rows),
            "fullPasses": sum(row["evaluation"]["passed"] == row["evaluation"]["total"] for row in rows),
            "meanScore": round(sum(row["evaluation"]["score"] for row in rows) / len(rows), 4),
            "meanModelInteractions": round(sum(row["modelInteractions"] for row in rows) / len(rows), 2),
            "meanRepairAttempts": round(sum(row["repairAttempts"] for row in rows) / len(rows), 2),
        }

    repo = _repo_state()
    prompt_material = {
        treatment: _treatment_prompt(root, treatment)
        for treatment in TREATMENTS
    }
    return {
        "lab": "ADP-001",
        "phase": "B — single-model development-pattern comparison",
        "runnerVersion": RUNNER_VERSION,
        "repositoryCommit": repo["commit"],
        "repositoryDirty": repo["dirty"],
        "modelAlias": model,
        "treatments": list(TREATMENTS),
        "repeats": repeats,
        "trialsStarted": len(records),
        "completed": sum("error" not in record for record in records),
        "errors": sum("error" in record for record in records),
        "promptDigest": _digest(prompt_material),
        "baselineDigest": hashlib.sha256(_read(root / "baseline.py").encode("utf-8")).hexdigest(),
        "hiddenTestsDigest": hashlib.sha256(_read(root / "tests_hidden.py").encode("utf-8")).hexdigest(),
        "byTreatment": by_treatment,
        "latencyMsTotal": sum(latencies),
        "usage": dict(usage),
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required for ADP-001 Phase B. The lab never stores or commits your key.", file=sys.stderr)
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

    output = Path(os.environ.get("ADP_LAB_OUTPUT", DEFAULT_OUTPUT))
    records: list[dict[str, Any]] = []
    total = len(selected) * repeats
    print(f"ADP-001 Phase B: {len(selected)} treatment(s) x {repeats} repeat(s) = {total} trial(s) using {model}")

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
            except Exception as exc:  # keep other treatments running
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
