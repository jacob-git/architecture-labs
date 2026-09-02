"""ADP-001 Phase B5 replication: repair-budget curves across multiple frozen starts."""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from .b4_evaluator import evaluate
from .phase_b5 import (
    DEFAULT_BUDGETS,
    DEFAULT_MODEL,
    _call_model,
    _digest,
    _generate_frozen_start,
    _parse_budgets,
    _repo_state,
    _run_budget_branch,
    _shared_prompt,
    _read,
)

RUNNER_VERSION = "adp-phase-b5-replication-runner-v1"
DEFAULT_STARTS = 10
DEFAULT_OUTPUT = Path("labs/adp_001/results/phase-b5-replication-latest.json")


def _parse_starts() -> int:
    raw = os.environ.get("ADP_B5_STARTS", str(DEFAULT_STARTS))
    value = int(raw)
    if value < 1:
        raise ValueError
    return value


def _usage_totals(frozen_call: dict[str, Any], records: list[dict[str, Any]]) -> Counter:
    usage = Counter()
    for key, value in (frozen_call.get("usage") or {}).items():
        if isinstance(value, (int, float)):
            usage[key] += value
    for record in records:
        for call in record.get("calls", []):
            for key, value in (call.get("usage") or {}).items():
                if isinstance(value, (int, float)):
                    usage[key] += value
    return usage


def _token_count(call: dict[str, Any]) -> int:
    usage = call.get("usage") or {}
    value = usage.get("total_tokens")
    return int(value) if isinstance(value, (int, float)) else 0


def main() -> int:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required for ADP-001 Phase B5 replication.", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parent
    model = os.environ.get("ADP_LAB_MODEL", DEFAULT_MODEL)
    try:
        budgets = _parse_budgets()
        starts = _parse_starts()
    except (ValueError, TypeError):
        print("ADP_B5_STARTS must be >= 1 and ADP_B5_REPAIR_BUDGETS must contain integers >= 0", file=sys.stderr)
        return 2

    print(
        "ADP-001 Phase B5 replication: "
        f"starts={starts}; budgets={','.join(map(str, budgets))}; model={model}"
    )

    start_records: list[dict[str, Any]] = []
    overall_usage = Counter()

    for start_index in range(1, starts + 1):
        print(f"\nstart {start_index}/{starts}")
        run_root = root / "results" / "b5-replication" / f"start-{start_index:02d}"
        run_root.mkdir(parents=True, exist_ok=True)

        # Generate one frozen candidate, then copy it into a start-specific location.
        frozen_file, frozen_call, frozen_parsed = _generate_frozen_start(root, api_key, model)
        frozen_source = frozen_file.read_text(encoding="utf-8")
        start_frozen = run_root / "frozen-start.py"
        start_frozen.write_text(frozen_source, encoding="utf-8")
        frozen_eval = evaluate(start_frozen, f"b5-replication-start-{start_index}")
        print(f"  frozen score={frozen_eval.score:.4f}")

        branch_records: list[dict[str, Any]] = []
        for budget in budgets:
            # _run_budget_branch writes under b5-runs, so temporarily use a copied frozen file,
            # then retain the full returned metadata in the replication result.
            record = _run_budget_branch(
                root=root,
                budget=budget,
                frozen_file=start_frozen,
                api_key=api_key,
                model=model,
            )
            branch_records.append(record)
            e = record["evaluation"]
            print(
                f"  budget={budget}: score={e['score']:.4f} "
                f"repairsUsed={record['repairsUsed']} "
                f"fullPass={e['passed'] == e['total']}"
            )

        usage = _usage_totals(frozen_call, branch_records)
        overall_usage.update(usage)
        start_record = {
            "start": start_index,
            "frozenStartDigest": _digest(frozen_parsed["implementation"]),
            "frozenStartScore": round(frozen_eval.score, 4),
            "frozenStartFullPass": frozen_eval.passed == frozen_eval.total,
            "frozenStartCall": {
                "latencyMs": frozen_call.get("latencyMs"),
                "usage": frozen_call.get("usage") or {},
                "responseModel": frozen_call.get("responseModel"),
            },
            "branches": branch_records,
            "usage": dict(usage),
        }
        start_records.append(start_record)
        (run_root / "result.json").write_text(json.dumps(start_record, indent=2) + "\n", encoding="utf-8")

    by_budget: dict[str, Any] = {}
    for budget in budgets:
        branches = [
            branch
            for start in start_records
            for branch in start["branches"]
            if branch["repairBudget"] == budget
        ]
        successes = [branch for branch in branches if branch["evaluation"]["passed"] == branch["evaluation"]["total"]]
        branch_tokens: list[int] = []
        successful_tokens: list[int] = []
        for branch in branches:
            total = sum(_token_count(call) for call in branch.get("calls", []))
            branch_tokens.append(total)
            if branch in successes:
                successful_tokens.append(total)

        by_budget[str(budget)] = {
            "starts": len(branches),
            "fullPasses": len(successes),
            "recoveryRate": round(len(successes) / len(branches), 4) if branches else None,
            "meanFinalScore": round(mean(branch["evaluation"]["score"] for branch in branches), 4) if branches else None,
            "meanRepairsUsed": round(mean(branch["repairsUsed"] for branch in branches), 2) if branches else None,
            "meanRepairTokens": round(mean(branch_tokens), 2) if branch_tokens else None,
            "meanRepairTokensOnSuccess": round(mean(successful_tokens), 2) if successful_tokens else None,
        }

    repo = _repo_state()
    summary = {
        "lab": "ADP-001",
        "phase": "B5 replication — repair budget curves across fixed starts",
        "runnerVersion": RUNNER_VERSION,
        "repositoryCommit": repo["commit"],
        "repositoryDirty": repo["dirty"],
        "modelAlias": model,
        "starts": starts,
        "repairBudgets": list(budgets),
        "sameFrozenStartWithinEachBudgetSet": True,
        "independentFrozenStartsAcrossSets": True,
        "initialPromptDigest": _digest(_shared_prompt(root)),
        "hiddenTestsDigest": _digest(_read(root / "b4_tests_hidden.py")),
        "byBudget": by_budget,
        "usage": dict(overall_usage),
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    output = Path(os.environ.get("ADP_LAB_OUTPUT", DEFAULT_OUTPUT))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"summary": summary, "starts": start_records}, indent=2) + "\n", encoding="utf-8")
    print("\n" + json.dumps(summary, indent=2))
    print(f"result={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
