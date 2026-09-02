"""ADP-001 Phase B4: isolate the value of runtime feedback and repair."""

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

from .b4_evaluator import EvaluationResult, evaluate

API_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_OUTPUT = Path("labs/adp_001/results/phase-b4-latest.json")
RUNNER_VERSION = "adp-phase-b4-runner-v1"
TREATMENTS = ("one_shot", "runtime_feedback_loop")
MAX_REPAIRS = 3

SYSTEM = """You are participating in a controlled software engineering experiment.
Return JSON only with exactly these keys: implementation, tests, summary.
The implementation must be complete Python source exposing class PublishingApi.
Import baseline types only from labs.adp_001.b4_baseline.
Do not use third party runtime libraries. Do not inspect hidden tests. Do not use Markdown fences."""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _digest(text: str) -> str:
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
        if item.get("type") == "message":
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    parts.append(content["text"])
    return "\n".join(parts).strip()


def _call_model(api_key: str, model: str, prompt: str) -> dict[str, Any]:
    payload = {"model": model, "reasoning": {"effort": "none"}, "input": [
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt},
    ]}
    request = urllib.request.Request(API_URL, data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI {exc.code}: {detail}") from exc
    return {"text": _output_text(body), "latencyMs": round((time.perf_counter() - started) * 1000), "usage": body.get("usage") or {}, "responseModel": body.get("model")}


def _parse(text: str) -> dict[str, str]:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    value = json.loads(cleaned)
    implementation = value.get("implementation")
    if not isinstance(implementation, str) or not implementation.strip():
        raise ValueError("model response must contain implementation")
    return {"implementation": implementation.strip() + "\n", "tests": value.get("tests", "") if isinstance(value.get("tests", ""), str) else "", "summary": value.get("summary", "") if isinstance(value.get("summary", ""), str) else ""}


def _shared_prompt(root: Path) -> str:
    baseline_public = """from dataclasses import dataclass\nfrom typing import Any\n\n@dataclass(frozen=True)\nclass Response:\n    status: int\n    body: dict[str, Any]\n\nclass TinyApi:\n    def __init__(self): self._items = {}\n    def put_item(self, client_id, key, value):\n        self._items[(client_id, key)] = value\n        return Response(200, {\"key\": key, \"value\": value})\n    def get_item(self, client_id, key):\n        value = self._items.get((client_id, key))\n        return Response(404, {\"error\": \"not_found\"}) if value is None else Response(200, {\"key\": key, \"value\": value})\n"""
    return f"{_read(root / 'b4_prompt.md')}\n\n# Starting application\n```python\n{baseline_public}\n```"


def _visible_feedback(evaluation: EvaluationResult) -> str:
    visible = next(c for c in evaluation.checks if c.name == "b4_tests_visible.py")
    dependency = next(c for c in evaluation.checks if c.name == "dependency_policy")
    return f"Visible integration tests: {'PASS' if visible.passed else 'FAIL'}\n{visible.detail}\n\nDependency policy: {'PASS' if dependency.passed else 'FAIL'}\n{dependency.detail}"


def _run_one(root: Path, treatment: str, trial: int, api_key: str, model: str) -> dict[str, Any]:
    run_dir = root / "results" / "b4-runs" / f"{treatment}-{trial:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    base_prompt = _shared_prompt(root)
    prompt = base_prompt
    calls: list[dict[str, Any]] = []
    repairs = 0
    max_attempts = 1 if treatment == "one_shot" else 1 + MAX_REPAIRS
    evaluation = None
    parsed = None
    candidate = None
    for attempt in range(1, max_attempts + 1):
        result = _call_model(api_key, model, prompt)
        parsed = _parse(result["text"])
        candidate = run_dir / f"candidate-attempt-{attempt}.py"
        candidate.write_text(parsed["implementation"], encoding="utf-8")
        evaluation = evaluate(candidate, treatment)
        calls.append({"attempt": attempt, "latencyMs": result["latencyMs"], "usage": result["usage"], "responseModel": result["responseModel"], "candidateDigest": _digest(parsed["implementation"])})
        visible = next(c for c in evaluation.checks if c.name == "b4_tests_visible.py")
        dependency = next(c for c in evaluation.checks if c.name == "dependency_policy")
        if treatment == "one_shot" or (visible.passed and dependency.passed):
            break
        if attempt < max_attempts:
            repairs += 1
            prompt = "\n\n".join([base_prompt, "# Current implementation", parsed["implementation"], "# Runtime validation feedback", _visible_feedback(evaluation), "Repair the integration using only this visible runtime feedback. Return the complete corrected implementation in the same JSON structure."])
    assert evaluation is not None and parsed is not None and candidate is not None
    return {"treatment": treatment, "trial": trial, "modelInteractions": len(calls), "repairAttempts": repairs, "calls": calls, "evaluation": evaluation.to_dict(), "finalCandidate": str(candidate.relative_to(root)), "summary": parsed["summary"]}


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required for ADP-001 Phase B4.", file=sys.stderr); return 2
    root = Path(__file__).resolve().parent
    model = os.environ.get("ADP_LAB_MODEL", DEFAULT_MODEL)
    repeats = int(os.environ.get("ADP_LAB_REPEATS", "1"))
    records: list[dict[str, Any]] = []
    total = repeats * len(TREATMENTS)
    print(f"ADP-001 Phase B4: 2 treatments x {repeats} repeat(s) = {total} trial(s) using {model}")
    position = 0
    for trial in range(1, repeats + 1):
        for treatment in TREATMENTS:
            position += 1
            print(f"[{position}/{total}] {treatment} trial {trial}")
            try:
                record = _run_one(root, treatment, trial, api_key, model)
                records.append(record)
                e = record["evaluation"]
                print(f"  score={e['score']:.4f} interactions={record['modelInteractions']} repairs={record['repairAttempts']}")
            except Exception as exc:
                records.append({"treatment": treatment, "trial": trial, "error": f"{type(exc).__name__}: {exc}"})
                print(f"  ERROR: {exc}", file=sys.stderr)
    by_treatment: dict[str, Any] = {}
    usage = Counter()
    for record in records:
        for call in record.get("calls", []):
            for k, v in (call.get("usage") or {}).items():
                if isinstance(v, (int, float)): usage[k] += v
    for treatment in TREATMENTS:
        rows = [r for r in records if r.get("treatment") == treatment and "error" not in r]
        by_treatment[treatment] = {"completed": len(rows), "fullPasses": sum(r["evaluation"]["passed"] == r["evaluation"]["total"] for r in rows), "meanScore": round(sum(r["evaluation"]["score"] for r in rows)/len(rows), 4) if rows else None, "meanModelInteractions": round(sum(r["modelInteractions"] for r in rows)/len(rows), 2) if rows else None, "meanRepairAttempts": round(sum(r["repairAttempts"] for r in rows)/len(rows), 2) if rows else None}
    repo = _repo_state()
    shared = _shared_prompt(root)
    summary = {"lab": "ADP-001", "phase": "B4 — runtime feedback value", "runnerVersion": RUNNER_VERSION, "repositoryCommit": repo["commit"], "repositoryDirty": repo["dirty"], "modelAlias": model, "treatments": list(TREATMENTS), "repeats": repeats, "trialsStarted": len(records), "completed": sum("error" not in r for r in records), "errors": sum("error" in r for r in records), "initialPromptDigest": _digest(shared), "sameInitialPromptForBothTreatments": True, "hiddenTestsDigest": _digest(_read(root / "b4_tests_hidden.py")), "byTreatment": by_treatment, "usage": dict(usage), "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    output = Path(os.environ.get("ADP_LAB_OUTPUT", DEFAULT_OUTPUT))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"summary": summary, "records": records}, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(summary, indent=2)); print(f"result={output}")
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
