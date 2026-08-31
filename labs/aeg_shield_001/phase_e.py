from __future__ import annotations

from datetime import timedelta
import json

from .core import Decision, Proposal
from .feedback_v3 import AEGGovernorV3, EvidenceMemoryV3, EvidenceRecordV3, sign_record
from .phase_c import NOW

SECRET = b"phase-e-lab-key"


def proposal(change_type: str, risk: float = 0.30) -> Proposal:
    return Proposal(f"phase-e-{change_type}", change_type, risk, 0.01, 180)


def evaluate(memory: EvidenceMemoryV3, change_type: str, environment: str, risk: float = 0.30) -> str:
    return AEGGovernorV3(memory, environment).evaluate(proposal(change_type, risk), now=NOW).decision.value


def signed_record(
    *,
    event_id: str,
    source_event_id: str,
    change_type: str,
    environment: str = "prod",
    occurred_at=NOW,
    severity: float = 0.45,
    kind: str = "incident",
    reason: str = "runtime evidence",
    producer: str = "shield-runtime",
) -> EvidenceRecordV3:
    record = EvidenceRecordV3(
        event_id=event_id,
        source_event_id=source_event_id,
        change_type=change_type,
        environment=environment,
        producer=producer,
        occurred_at=occurred_at,
        severity=severity,
        kind=kind,
        reason=reason,
    )
    return sign_record(record, SECRET)


def check_learning_preserved() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    accepted = memory.ingest(signed_record(event_id="learn-1", source_event_id="incident-1", change_type="routing_rule"), now=NOW)
    actual = evaluate(memory, "routing_rule", "prod", 0.35)
    return {"scenario": "phase_a_learning_preserved", "expected": Decision.DENY.value, "actual": actual, "accepted": accepted, "passed": accepted and actual == Decision.DENY.value}


def check_stale_evidence() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    memory.ingest(signed_record(event_id="old-1", source_event_id="old-source", change_type="routing_rule", occurred_at=NOW - timedelta(days=180)), now=NOW)
    actual = evaluate(memory, "routing_rule", "prod")
    return {"scenario": "stale_evidence", "expected": Decision.ALLOW.value, "actual": actual, "passed": actual == Decision.ALLOW.value}


def check_environment_scope() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    memory.ingest(signed_record(event_id="prod-1", source_event_id="prod-source", change_type="feature_flag", environment="prod"), now=NOW)
    actual = evaluate(memory, "feature_flag", "staging")
    return {"scenario": "environment_contamination", "expected": Decision.ALLOW.value, "actual": actual, "passed": actual == Decision.ALLOW.value}


def check_untrusted_producer() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    forged = EvidenceRecordV3("fake-1", "fake-source", "tool_permission", "prod", "untrusted-producer", NOW, 0.45, "incident", "poisoned")
    accepted = memory.ingest(forged, now=NOW)
    actual = evaluate(memory, "tool_permission", "prod")
    return {"scenario": "poisoned_feedback", "expected": Decision.ALLOW.value, "actual": actual, "accepted": accepted, "passed": (not accepted) and actual == Decision.ALLOW.value}


def check_bounded_aggregation() -> dict[str, object]:
    memory = EvidenceMemoryV3(max_penalty=0.60)
    for i in range(20):
        memory.ingest(signed_record(event_id=f"agg-{i}", source_event_id=f"source-{i}", change_type="routing_rule", severity=0.20), now=NOW)
    penalty = memory.penalty_for("routing_rule", "prod", now=NOW)
    return {"scenario": "bounded_aggregation", "expected_max": 0.60, "actual": penalty, "passed": penalty <= 0.60}


def check_future_timestamp() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    accepted = memory.ingest(signed_record(event_id="future-1", source_event_id="future-source", change_type="routing_rule", occurred_at=NOW + timedelta(days=365)), now=NOW)
    actual = evaluate(memory, "routing_rule", "prod", 0.30)
    return {"scenario": "future_timestamp", "expected": Decision.ALLOW.value, "actual": actual, "accepted": accepted, "passed": (not accepted) and actual == Decision.ALLOW.value}


def check_correlation_id_evasion() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    memory.ingest(signed_record(event_id="symptom-a", source_event_id="root-88", change_type="cache_policy", severity=0.25, reason="error symptom"), now=NOW)
    memory.ingest(signed_record(event_id="symptom-b", source_event_id="root-88", change_type="cache_policy", severity=0.25, reason="latency symptom"), now=NOW)
    actual = evaluate(memory, "cache_policy", "prod", 0.25)
    return {"scenario": "correlation_id_evasion", "expected": Decision.ALLOW.value, "actual": actual, "passed": actual == Decision.ALLOW.value}


def check_replay_resistance() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    original = signed_record(event_id="replay-0", source_event_id="replay-source", change_type="feature_flag", severity=0.20, reason="same incident payload")
    accepted_first = memory.ingest(original, now=NOW)
    replay = EvidenceRecordV3("replay-1", original.source_event_id, original.change_type, original.environment, original.producer, original.occurred_at, original.severity, original.kind, original.reason, original.signature)
    accepted_replay = memory.ingest(replay, now=NOW)
    actual = evaluate(memory, "feature_flag", "prod", 0.20)
    return {"scenario": "replay_with_new_ids", "expected": Decision.ALLOW.value, "actual": actual, "accepted_first": accepted_first, "accepted_replay": accepted_replay, "passed": accepted_first and (not accepted_replay) and actual == Decision.ALLOW.value}


def check_producer_authenticity() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    malicious = EvidenceRecordV3("compromised-1", "compromised-source", "tool_permission", "prod", "shield-runtime", NOW, 0.45, "incident", "malicious record", "not-a-valid-signature")
    accepted = memory.ingest(malicious, now=NOW)
    actual = evaluate(memory, "tool_permission", "prod", 0.30)
    return {"scenario": "trusted_producer_compromise", "expected": Decision.ALLOW.value, "actual": actual, "accepted": accepted, "passed": (not accepted) and actual == Decision.ALLOW.value}


def check_counterevidence() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    incident = signed_record(event_id="incident-9", source_event_id="source-9", change_type="routing_rule", severity=0.45, kind="incident", reason="severe failure")
    recovery = signed_record(event_id="recovery-9", source_event_id="source-9", change_type="routing_rule", occurred_at=NOW + timedelta(minutes=1), severity=0.0, kind="recovery", reason="verified successful recovery")
    accepted_incident = memory.ingest(incident, now=NOW + timedelta(minutes=1))
    accepted_recovery = memory.ingest(recovery, now=NOW + timedelta(minutes=1))
    actual = AEGGovernorV3(memory, "prod").evaluate(proposal("routing_rule", 0.30), now=NOW + timedelta(minutes=1)).decision.value
    return {"scenario": "verified_counterevidence", "expected": Decision.ALLOW.value, "actual": actual, "accepted_incident": accepted_incident, "accepted_recovery": accepted_recovery, "passed": accepted_incident and accepted_recovery and actual == Decision.ALLOW.value}


def run_phase_e() -> dict[str, object]:
    checks = [
        check_learning_preserved(),
        check_stale_evidence(),
        check_environment_scope(),
        check_untrusted_producer(),
        check_bounded_aggregation(),
        check_future_timestamp(),
        check_correlation_id_evasion(),
        check_replay_resistance(),
        check_producer_authenticity(),
        check_counterevidence(),
    ]
    passed = sum(1 for check in checks if check["passed"])
    return {
        "lab": "AEG × SHIELD Lab #001",
        "phase": "E — feedback memory v3 repair",
        "implementation": "feedback-memory-v3",
        "checks_passed": passed,
        "checks_total": len(checks),
        "repair_validated": passed == len(checks),
        "checks": checks,
    }


def main() -> None:
    result = run_phase_e()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["repair_validated"] else 1)


if __name__ == "__main__":
    main()
