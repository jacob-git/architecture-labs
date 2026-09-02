"""ADP-001 Phase B5: compare repair budgets from one frozen starting candidate."""

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
DEFAULT_OUTPUT = Path("labs/adp_001/results/phase-b5-latest.json")
RUNNER_VERSION = "adp-phase-b5-runner-v1"
DEFAULT_BUDGETS = (0, 1, 3, 5, 8)

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
    payload = {
        "model": model,
        "reasoning": {"effort": "none"},
        "input": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
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
        raise RuntimeError(f"OpenAI {exc.code}: {detail}") from exc
    return {
        "text": _output_text(body),
        "latencyMs": round((time.perf_counter() - started) * 1000),
        "usage": body.get("usage") or {},
        "responseModel": body.get("model"),
    }


def _parse(text: str) -> dict[str, str]:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    value = json.loads(cleaned)
    implementation = value.get("implementation")
    if not isinstance(implementation, str) or not implementation.strip():
        raise ValueError("model response must contain implementation")
    tests = value.get("tests", "")
    summary = value.get("summary", "")
    return {
        "implementation": implementation.strip() + "\n",
        "tests": tests if isinstance(tests, str) else "",
        "summary": summary if isinstance(summary, str) else "",
    }


def _shared_prompt(root: Path) -> str:
    baseline_public = """from dataclasses import dataclass\nfrom typing import Any\n\n@dataclass(frozen=True)\nclass Response:\n    status: int\n    body: dict[str, Any]\n\nclass TinyApi:\n    def __init__(self): self._items = {}\n    def put_item(self, client_id, key, value):\n        self._items[(client_id, key)] = value\n        return Response(200, {\"key\": key, \"value\": value})\n    def get_item(self, client_id, key):\n        value = self._items.get((client_id, key))\n        return Response(404, {\"error\": \"not_found\"}) if value is None else Response(200, {\"key\": key, \"value\": value})\n"""
    return f"{_read(root / 'b4_prompt.md')}\n\n# Starting application\n```python\n{baseline_public}\n```"


def _visible_feedback(evaluation: EvaluationResult) -> str:
    visible = next(c for c in evaluation.checks if c.name == "b4_tests_visible.py")
    dependency = next(c for c in evaluation.checks if c.name == "dependency_policy")
    return (
        f"Visible integration tests: {'PASS' if visible.passed else 'FAIL'}\n{visible.detail}\n\n"
        f"Dependency policy: {'PASS' if dependency.passed else 'FAIL'}\n{dependency.detail}"
    )


def _parse_budgets() -> tuple[int, ...]:
    raw = os.environ.get("ADP_B5_REPAIR_BUDGETS")
    if not raw:
        return DEFAULT_BUDGETS
    values: list[int] = []
    for part in raw.split(","):
        value = int(part.strip())
        if value < 0:
            raise ValueError
        values.append(value)
    if not values:
        raise ValueError
    return tuple(dict.fromkeys(values))


def _write_candidate(path: Path, parsed: dict[str, str]) -> None:
    path.write_text(parsed["implementation"], encoding="utf-8")


def _generate_frozen_start(root: Path, api_key: str, model: str) -> tuple[Path, dict[str, Any], dict[str, str]]:
    run_root = root / "results" / "b5-runs"
    run_root.mkdir(parents=True, exist_ok=True)
    frozen = run_root / "frozen-start.py"
    prompt = _shared_prompt(root)
    result = _call_model(api_key, model, prompt)
    parsed = _parse(result["text"])
    _write_candidate(frozen, parsed)
    (run_root / "frozen-start-summary.txt").write_text(parsed["summary"] + "\n", encoding="utf-8")
    return frozen, result, parsed


def _run_budget_branch(*, root: Path, budget: int, frozen_file: Path, api_key: str, model: str) -> dict[str, Any]:
    branch_dir = root / "results" / "b5-runs" / f"budget-{budget}"
    branch_dir.mkdir(parents=True, exist_ok=True)
    current_source = frozen_file.read_text(encoding="utf-8")
    current = branch_dir / "candidate-attempt-0.py"
    current.write_text(current_source, encoding="utf-8")
    evaluation = evaluate(current, f"b5-budget-{budget}")
    trajectory: list[dict[str, Any]] = [{
        "attempt": 0,
        "candidateDigest": _digest(current_source),
        "evaluation": evaluation.to_dict(),
        "modelCall": False,
    }]
    calls: list[dict[str, Any]] = []
    repairs = 0
    base_prompt = _shared_prompt(root)

    for repair_index in range(1, budget + 1):
        visible = next(c for c in evaluation.checks if c.name == "b4_tests_visible.py")
        dependency = next(c for c in evaluation.checks if c.name == "dependency_policy")
        if visible.passed and dependency.passed:
            break
        prompt = "\n\n".join([
            base_prompt,
            "# Frozen starting candidate lineage",
            "Every branch in this experiment began from the exact same initial candidate. Continue repairing only this branch from its current implementation.",
            "# Current implementation",
            current_source,
            "# Runtime validation feedback",
            _visible_feedback(evaluation),
            "Repair the integration using only this visible runtime feedback. Return the complete corrected implementation in the same JSON structure.",
        ])
        result = _call_model(api_key, model, prompt)
        parsed = _parse(result["text"])
        repairs += 1
        current_source = parsed["implementation"]
        current = branch_dir / f"candidate-attempt-{repair_index}.py"
        _write_candidate(current, parsed)
        evaluation = evaluate(current, f"b5-budget-{budget}")
        calls.append({
            "repair": repair_index,
            "latencyMs": result["latencyMs"],
            "usage": result["usage"],
            "responseModel": result["responseModel"],
            "candidateDigest": _digest(current_source),
        })
        trajectory.append({
            "attempt": repair_index,
            "candidateDigest": _digest(current_source),
            "evaluation": evaluation.to_dict(),
            "modelCall": True,
        })

    return {
        "repairBudget": budget,
        "repairsUsed": repairs,
        "modelInteractionsAfterFrozenStart": len(calls),
        "evaluation": evaluation.to_dict(),
        "finalCandidate": str(current.relative_to(root)),
        "calls": calls,
        "trajectory": trajectory,
    }


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required for ADP-001 Phase B5.", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parent
    model = os.environ.get("ADP_LAB_MODEL", DEFAULT_MODEL)
    try:
        budgets = _parse_budgets()
    except (ValueError, TypeError):
        print("ADP_B5_REPAIR_BUDGETS must be comma-separated integers >= 0", file=sys.stderr)
        return 2

    print(f"ADP-001 Phase B5: fixed starting candidate; budgets={','.join(map(str, budgets))}; model={model}")
    frozen_file, frozen_call, frozen_parsed = _generate_frozen_start(root, api_key, model)
    frozen_evaluation = evaluate(frozen_file, "b5-frozen-start")
    print(f"frozen start score={frozen_evaluation.score:.4f}")

    records: list[dict[str, Any]] = []
    for budget in budgets:
        print(f"budget={budget}")
        record = _run_budget_branch(root=root, budget=budget, frozen_file=frozen_file, api_key=api_key, model=model)
        records.append(record)
        e = record["evaluation"]
        print(f"  score={e['score']:.4f} repairsUsed={record['repairsUsed']}")

    usage = Counter()
    for key, value in (frozen_call.get("usage") or {}).items():
        if isinstance(value, (int, float)):
            usage[key] += value
    for record in records:
        for call in record["calls"]:
            for key, value in (call.get("usage") or {}).items():
                if isinstance(value, (int, float)):
                    usage[key] += value

    repo = _repo_state()
    shared = _shared_prompt(root)
    summary = {
        "lab": "ADP-001",
        "phase": "B5 — repair budget from a fixed starting candidate",
        "runnerVersion": RUNNER_VERSION,
        "repositoryCommit": repo["commit"],
        "repositoryDirty": repo["dirty"],
        "modelAlias": model,
        "repairBudgets": list(budgets),
        "frozenStartDigest": _digest(frozen_parsed["implementation"]),
        "frozenStartScore": round(frozen_evaluation.score, 4),
        "sameFrozenStartForAllBudgets": True,
        "initialPromptDigest": _digest(shared),
        "hiddenTestsDigest": _digest(_read(root / "b4_tests_hidden.py")),
        "byBudget": {
            str(record["repairBudget"]): {
                "repairsUsed": record["repairsUsed"],
                "finalScore": record["evaluation"]["score"],
                "fullPass": record["evaluation"]["passed"] == record["evaluation"]["total"],
            }
            for record in records
        },
        "usage": dict(usage),
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    output = Path(os.environ.get("ADP_LAB_OUTPUT", DEFAULT_OUTPUT))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"summary": summary, "records": records}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"result={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
