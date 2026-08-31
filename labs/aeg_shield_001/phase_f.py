from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
import json

from .core import Decision, Proposal
from .feedback_v3 import AEGGovernorV3, EvidenceMemoryV3, EvidenceRecordV3, sign_record
from .phase_c import NOW
from .phase_e import SECRET, signed_record

SECONDARY_SECRET = b"phase-f-secondary-key"


def proposal(change_type: str, risk: float = 0.30) -> Proposal:
    return Proposal(f"phase-f-{change_type}", change_type, risk, 0.01, 180)


def evaluate(memory: EvidenceMemoryV3, change_type: str, risk: float = 0.30, environment: str = "prod") -> str:
    return AEGGovernorV3(memory, environment).evaluate(proposal(change_type, risk), now=NOW).decision.value


def stolen_signing_key_attack() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    forged = signed_record(
        event_id="stolen-key-1",
        source_event_id="stolen-source",
        change_type="tool_permission",
        severity=0.45,
        reason="attacker possesses the trusted signing key",
    )
    accepted = memory.ingest(forged, now=NOW)
    actual = evaluate(memory, "tool_permission", 0.30)
    return {
        "scenario": "stolen_signing_key",
        "expected": Decision.ALLOW.value,
        "actual": actual,
        "accepted": accepted,
        "passed": (not accepted) and actual == Decision.ALLOW.value,
        "why": "A valid MAC cannot distinguish the legitimate producer from an attacker who has stolen the producer key.",
    }


def revoked_key_attack() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    # The key is assumed revoked operationally, but v3 has no key-version or revocation-time semantics.
    late_record = signed_record(
        event_id="revoked-key-1",
        source_event_id="revoked-source",
        change_type="routing_rule",
        severity=0.45,
        reason="record signed after the key should have been revoked",
    )
    accepted = memory.ingest(late_record, now=NOW)
    actual = evaluate(memory, "routing_rule", 0.30)
    return {
        "scenario": "revoked_key_still_accepted",
        "expected": Decision.ALLOW.value,
        "actual": actual,
        "accepted": accepted,
        "passed": (not accepted) and actual == Decision.ALLOW.value,
        "why": "Trusted keys need version and revocation semantics; possession alone should not grant indefinite authority.",
    }


def conflicting_trusted_producers_attack() -> dict[str, object]:
    memory = EvidenceMemoryV3(producer_secrets={
        "shield-runtime": SECRET,
        "recovery-verifier": SECONDARY_SECRET,
    })
    incident = signed_record(
        event_id="conflict-incident",
        source_event_id="conflict-source",
        change_type="feature_flag",
        severity=0.45,
        reason="primary runtime monitor reports severe failure",
    )
    recovery_unsigned = EvidenceRecordV3(
        event_id="conflict-recovery",
        source_event_id="conflict-source",
        change_type="feature_flag",
        environment="prod",
        producer="recovery-verifier",
        occurred_at=NOW + timedelta(minutes=1),
        severity=0.0,
        kind="recovery",
        reason="secondary trusted producer reports recovery",
    )
    recovery = sign_record(recovery_unsigned, SECONDARY_SECRET)
    memory.ingest(incident, now=NOW + timedelta(minutes=1))
    memory.ingest(recovery, now=NOW + timedelta(minutes=1))
    actual = AEGGovernorV3(memory, "prod").evaluate(proposal("feature_flag", 0.30), now=NOW + timedelta(minutes=1)).decision.value
    return {
        "scenario": "conflicting_trusted_producers",
        "expected": Decision.DENY.value,
        "actual": actual,
        "passed": actual == Decision.DENY.value,
        "why": "A recovery claim from a different trusted producer should not silently erase a severe incident without an explicit conflict policy.",
    }


def authenticated_causal_collision_attack() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    # Two independent incidents are authentically but incorrectly assigned the same source_event_id.
    memory.ingest(signed_record(event_id="causal-a", source_event_id="collision-7", change_type="cache_policy", severity=0.25, reason="independent backend failure"), now=NOW)
    memory.ingest(signed_record(event_id="causal-b", source_event_id="collision-7", change_type="cache_policy", severity=0.25, reason="independent cache failure"), now=NOW)
    actual = evaluate(memory, "cache_policy", 0.25)
    return {
        "scenario": "authenticated_causal_collision",
        "expected": Decision.DENY.value,
        "actual": actual,
        "passed": actual == Decision.DENY.value,
        "why": "Authenticity does not prove causal grouping; a wrong shared source identity can suppress genuinely independent evidence.",
    }


def partial_recovery_attack() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    incident = signed_record(event_id="partial-incident", source_event_id="partial-source", change_type="routing_rule", severity=0.45, reason="severe failure")
    partial = signed_record(
        event_id="partial-recovery",
        source_event_id="partial-source",
        change_type="routing_rule",
        occurred_at=NOW + timedelta(minutes=1),
        severity=0.50,
        kind="recovery",
        reason="only half of the failed dependency set recovered",
    )
    memory.ingest(incident, now=NOW + timedelta(minutes=1))
    memory.ingest(partial, now=NOW + timedelta(minutes=1))
    actual = AEGGovernorV3(memory, "prod").evaluate(proposal("routing_rule", 0.30), now=NOW + timedelta(minutes=1)).decision.value
    return {
        "scenario": "partial_recovery_erases_full_incident",
        "expected": Decision.DENY.value,
        "actual": actual,
        "passed": actual == Decision.DENY.value,
        "why": "v3 treats every recovery record as complete, so partial recovery can erase the full incident penalty.",
    }


def low_and_slow_flood_attack() -> dict[str, object]:
    memory = EvidenceMemoryV3()
    for i in range(8):
        memory.ingest(signed_record(
            event_id=f"drip-{i}",
            source_event_id=f"drip-source-{i}",
            change_type="deployment_policy",
            occurred_at=NOW - timedelta(hours=i),
            severity=0.08,
            reason="low-severity authenticated drip event",
        ), now=NOW)
    actual = evaluate(memory, "deployment_policy", 0.20)
    return {
        "scenario": "low_and_slow_evidence_flood",
        "expected": Decision.ALLOW.value,
        "actual": actual,
        "passed": actual == Decision.ALLOW.value,
        "why": "Per-record authenticity and a total cap do not provide rate, quota, or concentration controls against a slow stream of distinct evidence.",
    }


def run_phase_f() -> dict[str, object]:
    checks = [
        stolen_signing_key_attack(),
        revoked_key_attack(),
        conflicting_trusted_producers_attack(),
        authenticated_causal_collision_attack(),
        partial_recovery_attack(),
        low_and_slow_flood_attack(),
    ]
    passed = sum(1 for check in checks if check["passed"])
    return {
        "lab": "AEG × SHIELD Lab #001",
        "phase": "F — blind holdout against feedback memory v3",
        "implementation": "feedback-memory-v3-frozen",
        "checks_passed": passed,
        "checks_total": len(checks),
        "holdout_survived": passed == len(checks),
        "checks": checks,
    }


def main() -> None:
    result = run_phase_f()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["holdout_survived"] else 1)


if __name__ == "__main__":
    main()
