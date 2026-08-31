from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

from .core import Decision, Proposal
from .feedback_v2 import AEGGovernorV2, EvidenceMemoryV2, EvidenceRecordV2

NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def proposal(change_type: str, risk: float = 0.30) -> Proposal:
    return Proposal(f"phase-c-{change_type}", change_type, risk, 0.01, 180)


def evaluate(memory: EvidenceMemoryV2, change_type: str, environment: str, risk: float = 0.30) -> str:
    return AEGGovernorV2(memory, environment).evaluate(proposal(change_type, risk), now=NOW).decision.value


def check_learning_preserved() -> dict[str, object]:
    memory = EvidenceMemoryV2()
    memory.ingest(EvidenceRecordV2("routing_rule", "prod", "incident-1", "shield-runtime", NOW, 0.45, "severe runtime breach"))
    actual = evaluate(memory, "routing_rule", "prod", 0.35)
    return {"scenario": "phase_a_learning_preserved", "expected": Decision.DENY.value, "actual": actual, "passed": actual == Decision.DENY.value}


def check_stale_evidence() -> dict[str, object]:
    memory = EvidenceMemoryV2()
    memory.ingest(EvidenceRecordV2("routing_rule", "prod", "old-1", "shield-runtime", NOW - timedelta(days=180), 0.45, "old incident"))
    actual = evaluate(memory, "routing_rule", "prod")
    return {"scenario": "stale_evidence", "expected": Decision.ALLOW.value, "actual": actual, "passed": actual == Decision.ALLOW.value}


def check_correlation() -> dict[str, object]:
    memory = EvidenceMemoryV2()
    memory.ingest(EvidenceRecordV2("cache_policy", "prod", "root-17", "shield-runtime", NOW, 0.25, "error symptom"))
    memory.ingest(EvidenceRecordV2("cache_policy", "prod", "root-17", "shield-runtime", NOW, 0.25, "latency symptom"))
    actual = evaluate(memory, "cache_policy", "prod", 0.25)
    return {"scenario": "correlated_incidents", "expected": Decision.ALLOW.value, "actual": actual, "passed": actual == Decision.ALLOW.value}


def check_environment_scope() -> dict[str, object]:
    memory = EvidenceMemoryV2()
    memory.ingest(EvidenceRecordV2("feature_flag", "prod", "prod-1", "shield-runtime", NOW, 0.45, "production dependency failure"))
    actual = evaluate(memory, "feature_flag", "staging")
    return {"scenario": "environment_contamination", "expected": Decision.ALLOW.value, "actual": actual, "passed": actual == Decision.ALLOW.value}


def check_provenance() -> dict[str, object]:
    memory = EvidenceMemoryV2()
    accepted = memory.ingest(EvidenceRecordV2("tool_permission", "prod", "fake-1", "untrusted-producer", NOW, 0.45, "poisoned record"))
    actual = evaluate(memory, "tool_permission", "prod")
    return {"scenario": "poisoned_feedback", "expected": Decision.ALLOW.value, "actual": actual, "accepted": accepted, "passed": (not accepted) and actual == Decision.ALLOW.value}


def check_bounded_aggregation() -> dict[str, object]:
    memory = EvidenceMemoryV2(max_penalty=0.60)
    for i in range(20):
        memory.ingest(EvidenceRecordV2("routing_rule", "prod", f"incident-{i}", "shield-runtime", NOW, 0.20, "independent incident"))
    penalty = memory.penalty_for("routing_rule", "prod", now=NOW)
    return {"scenario": "bounded_aggregation", "expected_max": 0.60, "actual": penalty, "passed": penalty <= 0.60}


def run_phase_c() -> dict[str, object]:
    checks = [check_learning_preserved(), check_stale_evidence(), check_correlation(), check_environment_scope(), check_provenance(), check_bounded_aggregation()]
    passed = sum(1 for c in checks if c["passed"])
    return {"lab": "AEG × SHIELD Lab #001", "phase": "C — feedback memory v2 repair", "implementation": "feedback-memory-v2", "checks_passed": passed, "checks_total": len(checks), "repair_validated": passed == len(checks), "checks": checks}


def main() -> None:
    result = run_phase_c()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["repair_validated"] else 1)


if __name__ == "__main__":
    main()
