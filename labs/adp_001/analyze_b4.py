from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

VISIBLE_TESTS = (
    "test_successful_put_publishes_runtime_event",
    "test_existing_read_behavior_still_works",
)
HIDDEN_TESTS = (
    "test_multiple_updates_publish_in_order",
    "test_clients_remain_isolated",
    "test_reads_do_not_publish",
    "test_event_payload_is_fresh_per_write",
)


def _run_property(test_file: Path, test_name: str, candidate: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["ADP_B4_CANDIDATE_FILE"] = str(candidate.resolve())
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", f"{test_file}::{test_name}"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    detail = (proc.stdout + proc.stderr).strip()
    return {
        "name": test_name,
        "passed": proc.returncode == 0,
        "detail": detail[-1800:],
    }


def _dependency_check(candidate: Path) -> dict[str, Any]:
    forbidden = {"requests", "httpx", "fastapi", "flask", "pydantic"}
    text = candidate.read_text(encoding="utf-8")
    hits = sorted(name for name in forbidden if f"import {name}" in text or f"from {name}" in text)
    return {
        "name": "dependency_policy",
        "passed": not hits,
        "detail": "standard-library-only" if not hits else f"forbidden imports: {hits}",
    }


def _attempt_number(path: Path) -> int:
    match = re.search(r"candidate-attempt-(\d+)\.py$", path.name)
    return int(match.group(1)) if match else 0


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _transition(previous: dict[str, bool] | None, current: dict[str, bool]) -> dict[str, list[str]]:
    if previous is None:
        return {"fixed": [], "regressed": [], "unchanged_pass": [], "unchanged_fail": []}
    return {
        "fixed": sorted(name for name, passed in current.items() if passed and not previous.get(name, False)),
        "regressed": sorted(name for name, passed in current.items() if not passed and previous.get(name, False)),
        "unchanged_pass": sorted(name for name, passed in current.items() if passed and previous.get(name, False)),
        "unchanged_fail": sorted(name for name, passed in current.items() if not passed and not previous.get(name, False)),
    }


def _analyze_run(root: Path, run_dir: Path) -> dict[str, Any]:
    visible_file = root / "b4_tests_visible.py"
    hidden_file = root / "b4_tests_hidden.py"
    candidates = sorted(run_dir.glob("candidate-attempt-*.py"), key=_attempt_number)
    attempts: list[dict[str, Any]] = []
    previous: dict[str, bool] | None = None

    for candidate in candidates:
        checks = [
            *(_run_property(visible_file, name, candidate) for name in VISIBLE_TESTS),
            *(_run_property(hidden_file, name, candidate) for name in HIDDEN_TESTS),
            _dependency_check(candidate),
        ]
        state = {check["name"]: bool(check["passed"]) for check in checks}
        attempt = _attempt_number(candidate)
        summary_file = run_dir / f"summary-attempt-{attempt}.txt"
        attempts.append({
            "attempt": attempt,
            "candidate": str(candidate.relative_to(root)),
            "candidateDigest": _digest(candidate),
            "passedProperties": sum(state.values()),
            "totalProperties": len(state),
            "propertyScore": round(sum(state.values()) / len(state), 4),
            "properties": checks,
            "transitionFromPrevious": _transition(previous, state),
            "modelSummary": summary_file.read_text(encoding="utf-8").strip() if summary_file.exists() else "",
        })
        previous = state

    return {
        "run": run_dir.name,
        "attempts": attempts,
        "finalPropertyScore": attempts[-1]["propertyScore"] if attempts else None,
    }


def main() -> int:
    root = Path(__file__).resolve().parent
    runs_root = root / "results" / "b4-runs"
    if not runs_root.exists():
        print(f"No B4 runs found under {runs_root}", file=sys.stderr)
        return 2

    run_dirs = sorted(path for path in runs_root.iterdir() if path.is_dir() and list(path.glob("candidate-attempt-*.py")))
    analyses = [_analyze_run(root, run_dir) for run_dir in run_dirs]

    payload = {
        "lab": "ADP-001",
        "phase": "B4 repair trajectory analysis",
        "model_calls": 0,
        "runsAnalyzed": len(analyses),
        "runs": analyses,
    }
    output = root / "results" / "phase-b4-repair-trajectory.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"ADP-001 B4 repair trajectory: {len(analyses)} saved run(s)")
    for run in analyses:
        print(f"\n{run['run']}")
        for attempt in run["attempts"]:
            print(
                f"  attempt {attempt['attempt']}: "
                f"{attempt['passedProperties']}/{attempt['totalProperties']} "
                f"property score={attempt['propertyScore']:.4f}"
            )
            transition = attempt["transitionFromPrevious"]
            if transition["fixed"]:
                print(f"    fixed: {', '.join(transition['fixed'])}")
            if transition["regressed"]:
                print(f"    regressed: {', '.join(transition['regressed'])}")
            failed = [p["name"] for p in attempt["properties"] if not p["passed"]]
            if failed:
                print(f"    still failing: {', '.join(failed)}")
            else:
                print("    all properties pass")

    print(f"\nresult={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
