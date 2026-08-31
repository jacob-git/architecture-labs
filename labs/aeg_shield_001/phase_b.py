from __future__ import annotations

import json
from dataclasses import asdict

from .core import AEGGovernor, Decision, EvidenceMemory, IncidentEvidence, Proposal


def _decision(memory: EvidenceMemory, change_type: str, risk: float = 0.30) -> str:
    proposal = Proposal(
        proposal_id=f"phase-b-{change_type}",
        change_type=change_type,
        risk_score=risk,
        predicted_error_rate=0.01,
        predicted_latency_ms=180,
    )
    return AEGGovernor(memory).evaluate(proposal).decision.value


def stale_evidence_counterexample() -> dict[str, object]:
    memory = EvidenceMemory()
    # Represents a severe incident far outside the intended freshness window.
    memory.ingest(IncidentEvidence("routing_rule", 0.45, "incident from 180 days ago"))
    actual = _decision(memory, "routing_rule", 0.30)
    expected = Decision.ALLOW.value
    return {
        "scenario": "stale_evidence",
        "expected": expected,
        "actual": actual,
        "passed": actual == expected,
        "why": "Old incident evidence should expire or decay before governing a current proposal.",
        "observed_penalty": memory.penalty_for("routing_rule"),
    }


def correlated_incident_counterexample() -> dict[str, object]:
    memory = EvidenceMemory()
    # Two symptoms originate from the same root cause, but v1 counts both independently.
    memory.ingest(IncidentEvidence("cache_policy", 0.25, "root-cause-17: error-rate symptom"))
    memory.ingest(IncidentEvidence("cache_policy", 0.25, "root-cause-17: latency symptom"))
    actual = _decision(memory, "cache_policy", 0.25)
    expected = Decision.ALLOW.value
    return {
        "scenario": "correlated_incidents",
        "expected": expected,
        "actual": actual,
        "passed": actual == expected,
        "why": "Correlated symptoms from one root cause should not accumulate as independent evidence.",
        "observed_penalty": memory.penalty_for("cache_policy"),
    }


def environment_contamination_counterexample() -> dict[str, object]:
    memory = EvidenceMemory()
    # The v1 schema cannot represent environment, so a prod incident contaminates staging.
    memory.ingest(IncidentEvidence("feature_flag", 0.45, "production-only dependency failure"))
    actual = _decision(memory, "feature_flag", 0.30)
    expected = Decision.ALLOW.value
    return {
        "scenario": "environment_contamination",
        "expected": expected,
        "actual": actual,
        "passed": actual == expected,
        "why": "Evidence from one environment should not silently govern a different environment.",
        "observed_penalty": memory.penalty_for("feature_flag"),
    }


def poisoned_feedback_counterexample() -> dict[str, object]:
    memory = EvidenceMemory()
    # v1 accepts evidence without provenance, signature, producer identity, or authority checks.
    memory.ingest(IncidentEvidence("tool_permission", 0.45, "untrusted producer supplied this record"))
    actual = _decision(memory, "tool_permission", 0.30)
    expected = Decision.ALLOW.value
    return {
        "scenario": "poisoned_feedback",
        "expected": expected,
        "actual": actual,
        "passed": actual == expected,
        "why": "Untrusted evidence should not be able to change governance state.",
        "observed_penalty": memory.penalty_for("tool_permission"),
    }


def run_phase_b() -> dict[str, object]:
    checks = [
        stale_evidence_counterexample(),
        correlated_incident_counterexample(),
        environment_contamination_counterexample(),
        poisoned_feedback_counterexample(),
    ]
    passed = sum(1 for check in checks if check["passed"])
    return {
        "lab": "AEG × SHIELD Lab #001",
        "phase": "B — adversarial feedback integrity",
        "implementation": "feedback-memory-v1",
        "checks_passed": passed,
        "checks_total": len(checks),
        "feedback_v1_survived": passed == len(checks),
        "checks": checks,
    }


def main() -> None:
    result = run_phase_b()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["feedback_v1_survived"] else 1)


if __name__ == "__main__":
    main()
