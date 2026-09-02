"""ADP-001 Phase B3: isolate autonomous verification and repair."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .b2_evaluator import EvaluationResult, evaluate
from .phase_b2 import _call_model, _digest_text, _parse_json, _read, _visible_feedback

TREATMENTS = ("spec_one_shot", "agentic_loop")
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_OUTPUT = Path("labs/adp_001/results/phase-b3-latest.json")
RUNNER_VERSION = "adp-phase-b3-runner-v1"
MAX_REPAIRS = 3


def _repo_state() -> dict[str, Any]:
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], check=True, capture_output=True, text=True).stdout.strip())
        return {"commit": commit, "dirty": dirty}
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def _shared_initial_prompt(root: Path) -> str:
    sections = [
        "# Experiment condition\nBoth treatments receive exactly the same initial engineering information. The only treatment difference is whether visible validation feedback may be used for autonomous repair.",
        f"# Feature specification\n{_read(root / 'b2_prompts' / 'spec.md')}",
        f"# Starting baseline\n```python\n{_read(root / 'b2_baseline.py')}\n```",
    ]
    for name in ("ARCHITECTURE.md", "ENGINEERING_RULES.md", "AGENTS.md"):
        sections.append(f"# {name}\n{_read(root / 'b2_context' / name)}")
    return "\n\n".join(sections)


def _write_candidate(run_dir: Path, parsed: dict[str, str], attempt: int) -> Path:
    candidate = run_dir / f"candidate-attempt-{attempt}.py"
    candidate.write_text(parsed["implementation"], encoding="utf-8")
    (run_dir / f"generated-tests-attempt-{attempt}.py").write_text(parsed["tests"], encoding="utf-8")
    (run_dir / f"summary-attempt-{attempt}.txt").write_text(parsed["summary"] + "\n", encoding="utf-8")
    return candidate


def _run_one(*, root: Path, treatment: str, trial: int, api_key: str, model: str) -> dict[str, Any]:
    run_dir = root / "results" / "b3-runs" / f"{treatment}-{trial:02d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    base_prompt = _shared_initial_prompt(root)
    prompt = base_prompt
    interactions = 0
    repairs = 0
    calls: list[dict[str, Any]] = []
    candidate: Path | None = None
    parsed: dict[str, str] | None = None
    evaluation: EvaluationResult | None = None
    max_attempts = 1 if treatment == "spec_one_shot" else 1 + MAX_REPAIRS

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
        })

        visible = next(check for check in evaluation.checks if check.name == "b2_tests_visible.py")
        dependency = next(check for check in evaluation.checks if check.name == "dependency_policy")
        if treatment == "spec_one_shot" or (visible.passed and dependency.passed):
            break
        if attempt < max_attempts:
            repairs += 1
            prompt = "\n\n".join([
                base_prompt,
                "# Current implementation",
                f"```python\n{parsed['implementation']}\n```",
                "# Visible validation feedback",
                _visible_feedback(evaluation),
                "Repair the implementation autonomously. Hidden evaluator results are unavailable. Return the same JSON structure with the complete corrected implementation.",
            ])

    assert candidate is not None and parsed is not None and evaluation is not None
    return {
        "treatment": treatment,
        "trial": trial,
        "modelAlias": model,
        "modelInteractions": interactions,
        "repairAttempts": repairs,
        "calls": calls,
        "evaluation": evaluation.to_dict(),
        "finalCandidate": str(candidate.relative_to(root)),
        "summary": parsed["summary"],
    }


def _summarize(records: list[dict[str, Any]], *, model: str, repeats: int, root: Path) -> dict[str, Any]:
    usage = Counter()
    for record in records:
        for call in record.get("calls", []):
            for key, value in (call.get("usage") or {}).items():
                if isinstance(value, (int, float)):
                    usage[key] += value

    by_treatment: dict[str, Any] = {}
    for treatment in TREATMENTS:
        rows = [r for r in records if r.get("treatment") == treatment and "error" not in r]
        by_treatment[treatment] = {
            "completed": len(rows),
            "fullPasses": sum(r["evaluation"]["passed"] == r["evaluation"]["total"] for r in rows),
            "meanScore": round(sum(r["evaluation"]["score"] for r in rows) / len(rows), 4) if rows else None,
            "meanModelInteractions": round(sum(r["modelInteractions"] for r in rows) / len(rows), 2) if rows else None,
            "meanRepairAttempts": round(sum(r["repairAttempts"] for r in rows) / len(rows), 2) if rows else None,
        }

    repo = _repo_state()
    initial_prompt = _shared_initial_prompt(root)
    return {
        "lab": "ADP-001",
        "phase": "B3 — autonomy isolation with identical initial information",
        "runnerVersion": RUNNER_VERSION,
        "repositoryCommit": repo["commit"],
        "repositoryDirty": repo["dirty"],
        "modelAlias": model,
        "treatments": list(TREATMENTS),
        "repeats": repeats,
        "trialsStarted": len(records),
        "completed": sum("error" not in r for r in records),
        "errors": sum("error" in r for r in records),
        "initialPromptDigest": hashlib.sha256(initial_prompt.encode("utf-8")).hexdigest(),
        "sameInitialPromptForBothTreatments": True,
        "hiddenTestsDigest": _digest_text(_read(root / "b2_tests_hidden.py")),
        "byTreatment": by_treatment,
        "usage": dict(usage),
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required for ADP-001 Phase B3.", file=sys.stderr)
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

    records: list[dict[str, Any]] = []
    total = len(TREATMENTS) * repeats
    print(f"ADP-001 Phase B3: 2 treatments x {repeats} repeat(s) = {total} trial(s) using {model}")
    position = 0
    for trial in range(1, repeats + 1):
        for treatment in TREATMENTS:
            position += 1
            print(f"[{position}/{total}] {treatment} trial {trial}")
            try:
                record = _run_one(root=root, treatment=treatment, trial=trial, api_key=api_key, model=model)
                records.append(record)
                e = record["evaluation"]
                print(f"  score={e['score']:.4f} interactions={record['modelInteractions']} repairs={record['repairAttempts']}")
            except Exception as exc:
                records.append({"treatment": treatment, "trial": trial, "error": f"{type(exc).__name__}: {exc}"})
                print(f"  ERROR: {exc}", file=sys.stderr)

    summary = _summarize(records, model=model, repeats=repeats, root=root)
    payload = {"summary": summary, "records": records}
    output = Path(os.environ.get("ADP_LAB_OUTPUT", DEFAULT_OUTPUT))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"result={output}")
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
