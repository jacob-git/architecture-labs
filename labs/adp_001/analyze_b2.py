from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

TREATMENTS = ("vibe", "intent", "spec", "context", "agentic")
VISIBLE_PROPERTIES = (
    "test_cached_read_preserves_existing_behavior",
    "test_write_invalidates_cached_value",
    "test_entry_expires_after_ttl",
)
HIDDEN_PROPERTIES = (
    "test_clients_are_isolated",
    "test_404_is_not_sticky_after_later_write",
    "test_cached_response_cannot_be_mutated_by_caller",
    "test_cache_capacity_is_bounded_and_evicts_lru",
    "test_concurrent_reads_are_safe",
    "test_exact_ttl_boundary_is_expired",
)


def _run_property(root: Path, candidate: Path, filename: str, test_name: str) -> bool:
    env = os.environ.copy()
    env["ADP_B2_CANDIDATE_FILE"] = str(candidate.resolve())
    node = f"{root / filename}::{test_name}"
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", node],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return proc.returncode == 0


def _dependency_pass(candidate: Path) -> bool:
    forbidden = {"cachetools", "redis", "diskcache", "fastapi", "flask"}
    text = candidate.read_text(encoding="utf-8")
    return not any(f"import {name}" in text or f"from {name}" in text for name in forbidden)


def _latest_candidate(run_dir: Path) -> Path | None:
    candidates = sorted(run_dir.glob("candidate-attempt-*.py"))
    return candidates[-1] if candidates else None


def main() -> int:
    root = Path(__file__).resolve().parent
    runs_root = root / "results" / "b2-runs"
    if not runs_root.exists():
        print(f"No B2 runs found at {runs_root}", file=sys.stderr)
        return 2

    properties = [
        *(('visible', name, 'b2_tests_visible.py') for name in VISIBLE_PROPERTIES),
        *(('hidden', name, 'b2_tests_hidden.py') for name in HIDDEN_PROPERTIES),
    ]
    matrix: dict[str, dict[str, dict[str, int]]] = {
        treatment: {
            test_name: {"passed": 0, "total": 0}
            for _, test_name, _ in properties
        }
        for treatment in TREATMENTS
    }
    dependency = {treatment: {"passed": 0, "total": 0} for treatment in TREATMENTS}
    runs: list[dict[str, object]] = []

    for treatment in TREATMENTS:
        for run_dir in sorted(runs_root.glob(f"{treatment}-*")):
            candidate = _latest_candidate(run_dir)
            if candidate is None:
                continue
            result: dict[str, object] = {
                "treatment": treatment,
                "run": run_dir.name,
                "candidate": str(candidate.relative_to(root)),
                "properties": {},
            }
            property_results: dict[str, bool] = {}
            for group, test_name, filename in properties:
                passed = _run_property(root, candidate, filename, test_name)
                property_results[test_name] = passed
                matrix[treatment][test_name]["total"] += 1
                matrix[treatment][test_name]["passed"] += int(passed)
            dep_pass = _dependency_pass(candidate)
            dependency[treatment]["total"] += 1
            dependency[treatment]["passed"] += int(dep_pass)
            result["properties"] = property_results
            result["dependency_policy"] = dep_pass
            runs.append(result)

    summary: dict[str, object] = {}
    for treatment in TREATMENTS:
        summary[treatment] = {
            "properties": matrix[treatment],
            "dependency_policy": dependency[treatment],
        }

    payload = {
        "lab": "ADP-001",
        "analysis": "B2 property-level replay",
        "model_calls": 0,
        "runsAnalyzed": len(runs),
        "summary": summary,
        "runs": runs,
    }
    output = root / "results" / "phase-b2-property-analysis.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"ADP-001 B2 property analysis: {len(runs)} saved run(s)")
    for treatment in TREATMENTS:
        total_runs = dependency[treatment]["total"]
        print(f"\n{treatment}: {total_runs} run(s)")
        for _, test_name, _ in properties:
            cell = matrix[treatment][test_name]
            print(f"  {test_name}: {cell['passed']}/{cell['total']}")
        dep = dependency[treatment]
        print(f"  dependency_policy: {dep['passed']}/{dep['total']}")
    print(f"\nresult={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
