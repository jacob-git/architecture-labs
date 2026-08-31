from __future__ import annotations

from datetime import timedelta
import json

from .core import Decision
from .feedback_v2 import EvidenceMemoryV2, EvidenceRecordV2
from .phase_c import NOW, evaluate


def future_timestamp_attack() -> dict[str, object]:
    memory = EvidenceMemoryV2()
    memory.ingest(EvidenceRecordV2(
        "routing_rule", "prod", "future-1", "shield-runtime",
        NOW + timedelta(days=365), 0.45, "clock-skewed future incident",
    ))
    actual = evaluate(memory, "routing_rule", "prod", 0.30)
    return {
        "scenario": "future_timestamp",
        "expected": Decision.ALLOW.value,
        "actual": actual,
        "passed": actual == Decision.ALLOW.value,
        "why": "Evidence dated far in the future should be rejected or quarantined, not treated as fresh.",
    }


def correlation_id_evasion_attack() -> dict[str, object]:
    memory = EvidenceMemoryV2()
    # One root cause is presented with different correlation IDs.
    memory.ingest(EvidenceRecordV2("cache_policy", "prod", "forged-a", "shield-runtime", NOW, 0.25, "root-88 symptom one"))
    memory.ingest(EvidenceRecordV2("cache_policy", "prod", "forged-b", "shield-runtime", NOW, 0.25, "root-88 symptom two"))
    actual = evaluate(memory, "cache_policy", "prod", 0.25)
    return {
        "scenario": "correlation_id_evasion",
        "expected": Decision.ALLOW.value,
        "actual": actual,
        "passed": actual == Decision.ALLOW.value,
        "why": "Correlation protection should not depend entirely on a caller-supplied identifier.",
    }


def replay_with_new_ids_attack() -> dict[str, object]:
    memory = EvidenceMemoryV2()
    for i in range(3):
        memory.ingest(EvidenceRecordV2(
            "feature_flag", "prod", f"replay-{i}", "shield-runtime", NOW,
            0.20, "replayed copy of the same incident payload",
        ))
    actual = evaluate(memory, "feature_flag", "prod", 0.20)
    return {
        "scenario": "replay_with_new_ids",
        "expected": Decision.ALLOW.value,
        "actual": actual,
        "passed": actual == Decision.ALLOW.value,
        "why": "Replaying one incident under new IDs should not accumulate independent governance weight.",
    }


def trusted_producer_compromise_attack() -> dict[str, object]:
    memory = EvidenceMemoryV2()
    accepted = memory.ingest(EvidenceRecordV2(
        "tool_permission", "prod", "compromised-1", "shield-runtime", NOW,
        0.45, "malicious record emitted under trusted producer identity",
    ))
    actual = evaluate(memory, "tool_permission", "prod", 0.30)
    return {
        "scenario": "trusted_producer_compromise",
        "expected": Decision.ALLOW.value,
        "actual": actual,
        "accepted": accepted,
        "passed": (not accepted) and actual == Decision.ALLOW.value,
        "why": "Producer-name allowlisting alone cannot establish evidence authenticity or integrity.",
    }


def contradiction_without_counterevidence_attack() -> dict[str, object]:
    memory = EvidenceMemoryV2()
    memory.ingest(EvidenceRecordV2(
        "routing_rule", "prod", "incident-9", "shield-runtime", NOW,
        0.45, "severe failure followed by verified successful recovery",
    ))
    # v2 has no positive/counter-evidence type, so the later verified recovery cannot be represented.
    actual = evaluate(memory, "routing_rule", "prod", 0.30)
    return {
        "scenario": "missing_counterevidence",
        "expected": Decision.ALLOW.value,
        "actual": actual,
        "passed": actual == Decision.ALLOW.value,
        "why": "A memory that accepts only negative incident weight cannot represent verified contradictory recovery evidence.",
    }


def run_phase_d() -> dict[str, object]:
    checks = [
        future_timestamp_attack(),
        correlation_id_evasion_attack(),
        replay_with_new_ids_attack(),
        trusted_producer_compromise_attack(),
        contradiction_without_counterevidence_attack(),
    ]
    passed = sum(1 for check in checks if check["passed"])
    return {
        "lab": "AEG × SHIELD Lab #001",
        "phase": "D — blind holdout attack",
        "implementation": "feedback-memory-v2-frozen",
        "checks_passed": passed,
        "checks_total": len(checks),
        "holdout_survived": passed == len(checks),
        "checks": checks,
    }


def main() -> None:
    result = run_phase_d()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["holdout_survived"] else 1)


if __name__ == "__main__":
    main()
