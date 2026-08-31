from __future__ import annotations

import argparse
import json
import platform
import subprocess
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .core import Observation, stable_digest
from .phase_c import build_balanced_observations
from .scoring_v2 import SCORING_VERSION_V2, scoring_digest_v2
from .temporal_v1 import (
    TEMPORAL_MODEL_VERSION,
    TemporalEvent,
    temporal_config_digest,
    temporal_detector,
)

RUNNER_VERSION = "shield-phase-c2-runner-v1"
SCENARIO_VERSION = "shield-phase-c2-adversarial-v1"

PHASE_C2_SPEC = {
    "cross_fingerprint_recovery": {
        "failure_fingerprint": "dependency-x-timeout",
        "recovery_fingerprint": "dependency-y-timeout",
        "failure_minute": 0,
        "recovery_minute": 10,
        "failures_per_unit": 5,
        "max_allowed_confidence_drop": 0.02,
    },
    "mixed_stale_history": {
        "stale_minute": 0,
        "fresh_minute": 90,
        "stale_failures_per_unit": 100,
        "fresh_failures_per_unit": 1,
        "max_allowed_confidence_amplification": 0.05,
    },
    "out_of_order_recovery": {
        "initial_failure_minute": 0,
        "recovery_minute": 30,
        "newer_failure_minute": 40,
        "evaluation_minute": 50,
        "failures_per_unit": 5,
        "required_tier": "high",
    },
    "bursty_single_unit_recurrence": {
        "minute": 90,
        "failure_events": 500,
        "required_tier": "low",
    },
    "future_clock_skew": {
        "now_minute": 100,
        "future_event_minute": 102,
        "future_units": 12,
        "require_visible_difference_from_empty": True,
    },
    "timestamp_tie": {
        "minute": 30,
        "failures_per_unit": 5,
        "require_conflict_distinguishable_from_recovery_only": True,
    },
    "contradictory_order": {
        "minute": 30,
        "failures_per_unit": 5,
        "require_full_output_equality": True,
    },
}


def _units_with_fingerprint(fingerprint: str) -> tuple[Observation, ...]:
    return tuple(
        replace(observation, fingerprint=fingerprint)
        for observation in build_balanced_observations(12)
    )


def _failures(
    units: tuple[Observation, ...],
    minute: float,
    failures_per_unit: int,
) -> list[TemporalEvent]:
    return [
        TemporalEvent(unit, minute, "failure")
        for unit in units
        for _ in range(failures_per_unit)
    ]


def _recoveries(
    units: tuple[Observation, ...],
    minute: float,
) -> list[TemporalEvent]:
    return [TemporalEvent(unit, minute, "recovery") for unit in units]


def cross_fingerprint_recovery_analysis() -> dict[str, object]:
    spec = PHASE_C2_SPEC["cross_fingerprint_recovery"]
    failure_units = _units_with_fingerprint(str(spec["failure_fingerprint"]))
    recovery_units = _units_with_fingerprint(str(spec["recovery_fingerprint"]))

    failures = _failures(
        failure_units,
        float(spec["failure_minute"]),
        int(spec["failures_per_unit"]),
    )
    evaluation_minute = float(spec["recovery_minute"])
    baseline = temporal_detector(failures, evaluation_minute)
    with_unrelated_recovery = temporal_detector(
        [
            *failures,
            *_recoveries(recovery_units, evaluation_minute),
        ],
        evaluation_minute,
    )

    confidence_drop = round(
        float(baseline["confidence"])
        - float(with_unrelated_recovery["confidence"]),
        6,
    )
    max_allowed = float(spec["max_allowed_confidence_drop"])
    passed = (
        confidence_drop <= max_allowed
        and with_unrelated_recovery["activeEvidenceUnits"]
        == baseline["activeEvidenceUnits"]
    )

    return {
        "failureFingerprint": spec["failure_fingerprint"],
        "recoveryFingerprint": spec["recovery_fingerprint"],
        "baseline": baseline,
        "withUnrelatedRecovery": with_unrelated_recovery,
        "confidenceDrop": confidence_drop,
        "maxAllowedDrop": max_allowed,
        "passed": passed,
    }


def mixed_stale_history_analysis() -> dict[str, object]:
    spec = PHASE_C2_SPEC["mixed_stale_history"]
    units = build_balanced_observations(12)

    fresh = _failures(
        units,
        float(spec["fresh_minute"]),
        int(spec["fresh_failures_per_unit"]),
    )
    stale = _failures(
        units,
        float(spec["stale_minute"]),
        int(spec["stale_failures_per_unit"]),
    )
    now = float(spec["fresh_minute"])

    fresh_only = temporal_detector(fresh, now)
    with_stale_history = temporal_detector([*stale, *fresh], now)
    amplification = round(
        float(with_stale_history["confidence"])
        - float(fresh_only["confidence"]),
        6,
    )
    max_allowed = float(spec["max_allowed_confidence_amplification"])
    tier_escalated = (
        fresh_only["tier"] != "high"
        and with_stale_history["tier"] == "high"
    )

    return {
        "freshOnly": fresh_only,
        "withStaleHistory": with_stale_history,
        "confidenceAmplification": amplification,
        "maxAllowedAmplification": max_allowed,
        "tierEscalated": tier_escalated,
        "passed": amplification <= max_allowed and not tier_escalated,
    }


def out_of_order_recovery_analysis() -> dict[str, object]:
    spec = PHASE_C2_SPEC["out_of_order_recovery"]
    units = build_balanced_observations(12)

    initial_failures = _failures(
        units,
        float(spec["initial_failure_minute"]),
        int(spec["failures_per_unit"]),
    )
    recoveries = _recoveries(units, float(spec["recovery_minute"]))
    newer_failures = _failures(
        units,
        float(spec["newer_failure_minute"]),
        int(spec["failures_per_unit"]),
    )

    now = float(spec["evaluation_minute"])
    chronological = temporal_detector(
        [*initial_failures, *recoveries, *newer_failures],
        now,
    )
    delayed_recovery_arrival = temporal_detector(
        [*initial_failures, *newer_failures, *recoveries],
        now,
    )

    return {
        "chronological": chronological,
        "delayedRecoveryArrival": delayed_recovery_arrival,
        "passed": (
            chronological == delayed_recovery_arrival
            and delayed_recovery_arrival["tier"] == spec["required_tier"]
        ),
    }


def bursty_single_unit_analysis() -> dict[str, object]:
    spec = PHASE_C2_SPEC["bursty_single_unit_recurrence"]
    unit = build_balanced_observations(12)[0]
    events = [
        TemporalEvent(unit, float(spec["minute"]), "failure")
        for _ in range(int(spec["failure_events"]))
    ]
    result = temporal_detector(events, float(spec["minute"]))

    return {
        "profile": result,
        "passed": result["tier"] == spec["required_tier"],
    }


def future_clock_skew_analysis() -> dict[str, object]:
    spec = PHASE_C2_SPEC["future_clock_skew"]
    units = build_balanced_observations(int(spec["future_units"]))
    events = [
        TemporalEvent(unit, float(spec["future_event_minute"]), "failure")
        for unit in units
    ]
    now = float(spec["now_minute"])
    future_result = temporal_detector(events, now)
    empty_result = temporal_detector([], now)

    # Phase C correctly prevents future evidence from affecting current
    # confidence. This adversarial check asks for an additional property:
    # future-dated input should not be silently indistinguishable from no input.
    # The model may satisfy this later through rejection metadata, skew handling,
    # or another explicit diagnostic; this test does not prescribe which.
    visible = future_result != empty_result

    return {
        "futureEventCount": len(events),
        "futureEventMinute": spec["future_event_minute"],
        "evaluationMinute": spec["now_minute"],
        "futureResult": future_result,
        "emptyResult": empty_result,
        "visibleDifference": visible,
        "passed": visible,
    }


def timestamp_tie_analysis() -> dict[str, object]:
    spec = PHASE_C2_SPEC["timestamp_tie"]
    units = build_balanced_observations(12)
    minute = float(spec["minute"])
    failures = _failures(
        units,
        minute,
        int(spec["failures_per_unit"]),
    )
    recoveries = _recoveries(units, minute)

    conflict = temporal_detector([*failures, *recoveries], minute)
    recovery_only = temporal_detector(recoveries, minute)

    # A tied contradictory observation set should be distinguishable from a
    # clean recovery-only set. This can be satisfied by retained evidence or an
    # explicit ambiguity diagnostic; the check does not require one resolution.
    distinguishable = conflict != recovery_only

    return {
        "conflict": conflict,
        "recoveryOnly": recovery_only,
        "distinguishable": distinguishable,
        "passed": distinguishable,
    }


def contradictory_order_analysis() -> dict[str, object]:
    spec = PHASE_C2_SPEC["contradictory_order"]
    units = build_balanced_observations(12)
    minute = float(spec["minute"])
    events = [
        *_failures(units, minute, int(spec["failures_per_unit"])),
        *_recoveries(units, minute),
    ]

    forward = temporal_detector(events, minute)
    reversed_result = temporal_detector(list(reversed(events)), minute)

    return {
        "forward": forward,
        "reversed": reversed_result,
        "passed": forward == reversed_result,
    }


def repository_provenance() -> tuple[str, bool | None]:
    root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return "unknown", None


def build_report() -> dict[str, object]:
    cross_fingerprint = cross_fingerprint_recovery_analysis()
    stale_history = mixed_stale_history_analysis()
    out_of_order = out_of_order_recovery_analysis()
    bursty = bursty_single_unit_analysis()
    clock_skew = future_clock_skew_analysis()
    timestamp_tie = timestamp_tie_analysis()
    contradictory_order = contradictory_order_analysis()
    commit, dirty = repository_provenance()

    checks = {
        "crossFingerprintRecoveryIsolated": cross_fingerprint["passed"],
        "staleHistoryCannotAmplifyFreshEvidence": stale_history["passed"],
        "delayedRecoveryDoesNotEraseNewerFailure": out_of_order["passed"],
        "burstySingleUnitRecurrenceRemainsLow": bursty["passed"],
        "futureClockSkewIsVisible": clock_skew["passed"],
        "timestampTieDoesNotHideContradiction": timestamp_tie["passed"],
        "contradictoryInputOrderInvariant": contradictory_order["passed"],
    }

    return {
        "lab": "SHIELD Lab #001",
        "phase": "C2 — adversarial temporal robustness",
        "runnerVersion": RUNNER_VERSION,
        "scenarioVersion": SCENARIO_VERSION,
        "temporalModelVersion": TEMPORAL_MODEL_VERSION,
        "baseScoringVersion": SCORING_VERSION_V2,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "scenarioDigest": stable_digest(PHASE_C2_SPEC),
        "temporalConfigDigest": temporal_config_digest(),
        "baseScoringDigest": scoring_digest_v2(),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "phaseConfig": PHASE_C2_SPEC,
        "analyses": {
            "crossFingerprintRecovery": cross_fingerprint,
            "mixedStaleHistory": stale_history,
            "outOfOrderRecovery": out_of_order,
            "burstySingleUnitRecurrence": bursty,
            "futureClockSkew": clock_skew,
            "timestampTie": timestamp_tie,
            "contradictoryOrder": contradictory_order,
        },
        "claimChecks": checks,
        "summary": {
            "claimPasses": sum(bool(value) for value in checks.values()),
            "claimCount": len(checks),
            "allPassed": all(checks.values()),
        },
        "interpretation": (
            "Phase C2 attacks the frozen shield-temporal-evidence-v1 model. "
            "A FAIL is a valid experimental result: it identifies temporal "
            "assumptions that require an explicitly versioned revision rather "
            "than weakening the adversarial checks."
        ),
        "limitations": [
            "All scenarios are deterministic synthetic proxies for distributed telemetry behavior.",
            "Cross-fingerprint isolation assumes a temporal detector may receive mixed fingerprints; a production pipeline could instead enforce fingerprint partitioning before scoring, but that invariant must then be explicit and tested.",
            "The stale-history amplification threshold is a stress criterion, not a universal calibration target.",
            "Clock-skew visibility does not prescribe whether future timestamps should be rejected, clamped, quarantined, or accepted within a bounded tolerance.",
            "The timestamp-tie check requires contradictory evidence to remain observable but does not prescribe which signal should win.",
            "No source trust, signed telemetry, network delay distribution, incident ground truth, or remediation action is modeled.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    analyses = report["analyses"]
    summary = report["summary"]
    lines = [
        "# SHIELD Lab #001 — Phase C2 Summary",
        "",
        f"**Overall:** {'PASS' if summary['allPassed'] else 'FAIL'}  ",
        f"**Temporal model:** `{report['temporalModelVersion']}`  ",
        f"**Base scoring:** `{report['baseScoringVersion']}`  ",
        f"**Repository:** `{report['repositoryCommit']}` (dirty={report['repositoryDirty']})  ",
        f"**Scenario digest:** `{report['scenarioDigest']}`  ",
        f"**Temporal config digest:** `{report['temporalConfigDigest']}`",
        "",
        "## Claim checks",
        "",
    ]
    for name, passed in report["claimChecks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")

    cross = analyses["crossFingerprintRecovery"]
    stale = analyses["mixedStaleHistory"]
    out_of_order = analyses["outOfOrderRecovery"]
    bursty = analyses["burstySingleUnitRecurrence"]["profile"]
    skew = analyses["futureClockSkew"]
    tie = analyses["timestampTie"]

    lines.extend(
        [
            "",
            "## Adversarial findings",
            "",
            "| Attack | Measurement | Result |",
            "|---|---:|---|",
            (
                "| Cross-fingerprint recovery | "
                f"confidence drop `{cross['confidenceDrop']:.6f}` | "
                f"{'PASS' if cross['passed'] else 'FAIL'} |"
            ),
            (
                "| Mixed stale history | "
                f"confidence amplification `{stale['confidenceAmplification']:.6f}` | "
                f"{'PASS' if stale['passed'] else 'FAIL'} |"
            ),
            (
                "| Delayed recovery arrival | "
                f"confidence `{out_of_order['delayedRecoveryArrival']['confidence']:.6f}` | "
                f"{'PASS' if out_of_order['passed'] else 'FAIL'} |"
            ),
            (
                "| 500-event single-unit burst | "
                f"confidence `{bursty['confidence']:.6f}` | "
                f"{'PASS' if analyses['burstySingleUnitRecurrence']['passed'] else 'FAIL'} |"
            ),
            (
                "| +2 minute future clock skew | "
                f"visible `{str(skew['visibleDifference']).lower()}` | "
                f"{'PASS' if skew['passed'] else 'FAIL'} |"
            ),
            (
                "| Same-timestamp failure/recovery | "
                f"distinguishable `{str(tie['distinguishable']).lower()}` | "
                f"{'PASS' if tie['passed'] else 'FAIL'} |"
            ),
        ]
    )

    lines.extend(
        [
            "",
            "## Key comparisons",
            "",
            (
                f"- Cross-fingerprint baseline confidence: "
                f"`{cross['baseline']['confidence']:.6f}`"
            ),
            (
                f"- After unrelated-fingerprint recovery: "
                f"`{cross['withUnrelatedRecovery']['confidence']:.6f}`"
            ),
            (
                f"- Fresh-only confidence: "
                f"`{stale['freshOnly']['confidence']:.6f}`"
            ),
            (
                f"- Fresh plus stale-history confidence: "
                f"`{stale['withStaleHistory']['confidence']:.6f}`"
            ),
            "",
            "## Interpretation",
            "",
            report["interpretation"],
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run SHIELD Lab #001 Phase C2 adversarial temporal tests."
    )
    parser.add_argument(
        "--output",
        default="labs/shield_001/results/phase-c2-latest.json",
        help="JSON result path.",
    )
    parser.add_argument(
        "--summary-output",
        help="Markdown summary path. Defaults beside the JSON result.",
    )
    args = parser.parse_args()

    report = build_report()
    output = Path(args.output)
    summary_output = (
        Path(args.summary_output)
        if args.summary_output
        else output.with_suffix(".summary.md")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary_output.write_text(render_summary(report), encoding="utf-8")

    print(render_summary(report))
    print(f"JSON:    {output}")
    print(f"Summary: {summary_output}")

    raise SystemExit(0 if report["summary"]["allPassed"] else 2)


if __name__ == "__main__":
    main()
