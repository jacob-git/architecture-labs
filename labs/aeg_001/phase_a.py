"""Phase A: deterministic adversarial integration validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import (
    POLICY_VERSION, clone, create_approved_command, digest, direct_executor,
    governed_executor, issue_approval, policy_v1,
)

LAB_DIR = Path(__file__).resolve().parent


def _attack_approval(scenario: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any] | None:
    attack_type = scenario.get("attack", {}).get("type")
    if not attack_type:
        return issue_approval(proposal) if scenario.get("approvalGranted") else None
    if attack_type == "forged_approval":
        return {"intentDigest": digest(proposal), "policyVersion": POLICY_VERSION, "expiresAt": 4_102_444_800_000, "nonce": "forged", "consumed": False, "signature": "forged"}
    if attack_type == "approval_for_other_target":
        altered = {"tool": proposal["tool"], "args": {**proposal["args"], "service": "lumen-worker"}}
        return issue_approval(altered)
    if attack_type == "approval_for_other_tool":
        return issue_approval({"tool": "config.update", "args": {"service": "lumen-api", "scope": "production", "key": "logLevel", "value": "warn"}})
    if attack_type == "expired_approval":
        return issue_approval(proposal, expired=True)
    if attack_type == "replay_consumed_approval":
        return issue_approval(proposal, consumed=True)
    if attack_type == "wrong_policy_version":
        return issue_approval(proposal, policy_version="policy-v0")
    if attack_type in {"mutate_after_approval", "mutate_signed_command"}:
        return issue_approval(proposal)
    return issue_approval(proposal) if scenario.get("approvalGranted") else None


def run_governed(scenario: dict[str, Any]) -> dict[str, Any]:
    proposal = clone(scenario["proposal"])
    decision = policy_v1(proposal, {"restartCountInWindow": scenario.get("restartCountInWindow")})
    approval = _attack_approval(scenario, proposal)
    attack = scenario.get("attack", {})

    if attack.get("type") == "mutate_after_approval":
        proposal = {"tool": proposal["tool"], "args": clone(attack["mutatedArgs"])}

    issued_command, approval_status = create_approved_command(proposal, decision, approval)
    command = clone(issued_command)

    if scenario.get("mutateAfterGovernance") is not None:
        proposal["args"] = clone(scenario["mutateAfterGovernance"])
    if attack.get("type") == "mutate_signed_command" and command:
        command["args"][attack["field"]] = attack["value"]

    executor_outcome = {"executed": False, "tool": scenario["proposal"].get("tool"), "args": None}
    enforcement_error = None
    try:
        if attack.get("type") == "raw_executor_call":
            governed_executor(clone(scenario["proposal"]))
        elif attack.get("type") == "fabricated_command":
            governed_executor({"kind": "ApprovedCommand", "tool": proposal["tool"], "args": clone(proposal["args"]), "policyVersion": POLICY_VERSION, "intentDigest": digest(proposal), "commandSignature": "fabricated"})
        elif command:
            executor_outcome = governed_executor(command)
    except ValueError as exc:
        enforcement_error = str(exc)

    effective_outcome = "approved" if decision["outcome"] == "requires_approval" and executor_outcome["executed"] else decision["outcome"]
    trace = {
        "scenario": scenario["id"], "proposal": clone(scenario["proposal"]), "decision": clone(decision),
        "command": {"tool": issued_command["tool"], "args": clone(issued_command["args"]), "policyVersion": issued_command["policyVersion"]} if issued_command else None,
        "execution": clone(executor_outcome),
    }
    if attack.get("type") == "drop_trace":
        trace.pop(attack["field"], None)
    trace_complete = all(key in trace for key in ("scenario", "proposal", "decision", "command", "execution"))
    trace_match = "expectedTraceComplete" not in scenario or trace_complete == scenario["expectedTraceComplete"]
    expected_args = scenario.get("expectedExecutedArgs", scenario["expected"].get("executedArgs"))
    args_match = expected_args is None or executor_outcome["args"] == expected_args
    passed = effective_outcome == scenario["expected"]["governanceOutcome"] and executor_outcome["executed"] == scenario["expected"]["executed"] and args_match and trace_match

    failure = None
    if not passed:
        failure = "COMMAND_INTEGRITY_FAILURE" if not args_match else "AUDIT_TRACE_GAP_NOT_DETECTED" if not trace_match else "ENFORCEMENT_MISMATCH" if enforcement_error else "POLICY_OR_EXECUTION_MISMATCH"
    return {
        "scenarioId": scenario["id"], "category": scenario["category"], "risk": scenario["risk"],
        "mode": "aeg", "policyVersion": POLICY_VERSION, "decision": decision,
        "approvalStatus": approval_status, "effectiveOutcome": effective_outcome,
        "executed": executor_outcome["executed"], "executedArgs": executor_outcome["args"],
        "enforcementError": enforcement_error, "traceComplete": trace_complete,
        "result": "pass" if passed else "fail", "failureClass": failure,
    }


def run_scenarios(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    governed = [run_governed(scenario) for scenario in scenarios]
    baseline = []
    for scenario in scenarios:
        outcome = direct_executor(clone(scenario["proposal"]))
        baseline.append({"scenarioId": scenario["id"], "mode": "baseline", "executed": outcome["executed"], "executedArgs": outcome.get("args"), "unsafeExecution": not scenario["expected"]["executed"] and outcome["executed"]})

    unsafe_ids = {s["id"] for s in scenarios if not s["expected"]["executed"]}
    attack_ids = {s["id"] for s in scenarios if s.get("attack") or s["category"] != "normal_legitimate"}
    categories = {}
    for category in dict.fromkeys(s["category"] for s in scenarios):
        records = [r for r in governed if r["category"] == category]
        categories[category] = {"scenarios": len(records), "passes": sum(r["result"] == "pass" for r in records)}

    passed = sum(result["result"] == "pass" for result in governed)
    unsafe_count = len(unsafe_ids)
    direct_unsafe = sum(r["scenarioId"] in unsafe_ids and r["executed"] for r in baseline)
    governed_unsafe = sum(r["scenarioId"] in unsafe_ids and r["executed"] for r in governed)
    summary = {
        "lab": "AEG Lab #001", "phase": "A — deterministic adversarial integration tests",
        "scenarios": len(scenarios), "governedPasses": passed, "governedFailures": len(governed) - passed,
        "attackOrEdgeCaseScenarios": len(attack_ids),
        "attackOrEdgeCasePasses": sum(r["scenarioId"] in attack_ids and r["result"] == "pass" for r in governed),
        "unsafeScenarioCount": unsafe_count, "baselineUnsafeExecuted": direct_unsafe,
        "aegUnsafeExecuted": governed_unsafe,
        "baselineUnsafeExecutionRate": direct_unsafe / unsafe_count if unsafe_count else 0,
        "aegUnsafeExecutionRate": governed_unsafe / unsafe_count if unsafe_count else 0,
        "approvedCommandIntegrityChecks": sum(bool(s.get("expectedExecutedArgs") or s["expected"].get("executedArgs")) for s in scenarios),
        "auditGapDetectionCases": sum(s.get("attack", {}).get("type") == "drop_trace" for s in scenarios),
        "policyVersion": POLICY_VERSION, "byCategory": categories,
    }
    return {"summary": summary, "aegResults": governed, "baselineResults": baseline}


def main() -> int:
    scenarios = json.loads((LAB_DIR / "scenarios.json").read_text(encoding="utf-8"))
    result = run_scenarios(scenarios)
    print(json.dumps(result, indent=2))
    return 1 if result["summary"]["governedFailures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
