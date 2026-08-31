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
from .temporal_v1 import TemporalEvent
from .temporal_v2 import (
    TEMPORAL_MODEL_VERSION_V2,
    temporal_config_digest_v2,
    temporal_detector_v2,
)

RUNNER_VERSION = "shield-phase-d-runner-v1"
SCENARIO_VERSION = "shield-phase-d-temporal-holdout-v1"

PHASE_D_SPEC = {
    "mixed_fingerprint_non_reinforcement": {
        "fingerprints": ["dependency-x-timeout", "dependency-y-timeout"],
        "units_per_fingerprint": 6,
        "failures_per_unit": 5,
        "max_allowed_confidence_amplification": 0.05,
        "combined_must_not_cross_high_if_components_below_high": True,
    },
    "stale_diverse_amplification": {
        "stale_minute": 0,
        "fresh_minute": 120,
        "fresh_units": 9,
        "fresh_failures_per_unit": 1,
        "stale_units": 3,
        "stale_failures_per_unit": 100,
        "max_allowed_confidence_amplification": 0.05,
        "no_tier_escalation": True,
    },
    "time_translation": {
        "shift_minutes": 1000,
        "evaluation_minute": 80,
    },
    "delayed_pre_recovery_replay": {
        "initial_failure_minute": 0,
        "recovery_minute": 30,
        "recurrence_minute": 60,
        "replay_event_minute": 20,
        "evaluation_minute": 60,
    },
    "repeated_recovery_idempotence": {
        "failure_minute": 0,
        "recovery_minutes": [30, 40, 50],
        "evaluation_minute": 60,
    },
    "future_data_isolation": {
        "current_minute": 100,
        "future_minute": 105,
        "current_units": 6,
        "future_units": 6,
    },
    "recurrence_reset": {
        "historical_failure_minute": 0,
        "recovery_minute": 60,
        "recurrence_minute": 120,
        "historical_failures_per_unit": 100,
        "fresh_failures_per_unit": 1,
    },
}


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


def mixed_fingerprint_analysis() -> dict[str, object]:
    spec = PHASE_D_SPEC["mixed_fingerprint_non_reinforcement"]
    base_units = build_balanced_observations(12)
    fp_a, fp_b = spec["fingerprints"]
    units_per_fingerprint = int(spec["units_per_fingerprint"])

    units_a = tuple(
        replace(unit, fingerprint=str(fp_a))
        for unit in base_units[:units_per_fingerprint]
    )
    units_b = tuple(
        replace(unit, fingerprint=str(fp_b))
        for unit in base_units[units_per_fingerprint : 2 * units_per_fingerprint]
    )
    failures_per_unit = int(spec["failures_per_unit"])
    events_a = _failures(units_a, 0.0, failures_per_unit)
    events_b = _failures(units_b, 0.0, failures_per_unit)

    result_a = temporal_detector_v2(events_a, 0.0)
    result_b = temporal_detector_v2(events_b, 0.0)
    combined = temporal_detector_v2([*events_a, *events_b], 0.0)

    component_max = max(
        float(result_a["confidence"]),
        float(result_b["confidence"]),
    )
    amplification = round(float(combined["confidence"]) - component_max, 6)
    max_allowed = float(spec["max_allowed_confidence_amplification"])
    tier_escalated = (
        result_a["tier"] != "high"
        and result_b["tier"] != "high"
        and combined["tier"] == "high"
    )

    return {
        "fingerprintA": result_a,
        "fingerprintB": result_b,
        "combined": combined,
        "confidenceAmplification": amplification,
        "maxAllowedAmplification": max_allowed,
        "tierEscalated": tier_escalated,
        "passed": (
            amplification <= max_allowed
            and not tier_escalated
        ),
    }


def stale_diverse_amplification_analysis() -> dict[str, object]:
    spec = PHASE_D_SPEC["stale_diverse_amplification"]
    units = build_balanced_observations(12)
    fresh_units = units[: int(spec["fresh_units"])]
    stale_units = units[-int(spec["stale_units"]) :]

    fresh_events = _failures(
        fresh_units,
        float(spec["fresh_minute"]),
        int(spec["fresh_failures_per_unit"]),
    )
    stale_events = _failures(
        stale_units,
        float(spec["stale_minute"]),
        int(spec["stale_failures_per_unit"]),
    )
    now = float(spec["fresh_minute"])

    fresh_only = temporal_detector_v2(fresh_events, now)
    with_stale_diversity = temporal_detector_v2(
        [*stale_events, *fresh_events],
        now,
    )
    amplification = round(
        float(with_stale_diversity["confidence"])
        - float(fresh_only["confidence"]),
        6,
    )
    max_allowed = float(spec["max_allowed_confidence_amplification"])
    tier_escalated = (
        fresh_only["tier"] != "high"
        and with_stale_diversity["tier"] == "high"
    )

    return {
        "freshOnly": fresh_only,
        "withStaleDiversity": with_stale_diversity,
        "confidenceAmplification": amplification,
        "maxAllowedAmplification": max_allowed,
        "tierEscalated": tier_escalated,
        "passed": amplification <= max_allowed and not tier_escalated,
    }


def time_translation_analysis() -> dict[str, object]:
    spec = PHASE_D_SPEC["time_translation"]
    units = build_balanced_observations(12)
    events = [
        *_failures(units, 10.0, 2),
        *_recoveries(units[:4], 40.0),
        *_failures(units[:4], 70.0, 1),
    ]
    now = float(spec["evaluation_minute"])
    shift = float(spec["shift_minutes"])

    base = temporal_detector_v2(events, now)
    shifted_events = [
        TemporalEvent(event.observation, event.minute + shift, event.state)
        for event in events
    ]
    shifted = temporal_detector_v2(shifted_events, now + shift)

    return {
        "base": base,
        "shifted": shifted,
        "shiftMinutes": shift,
        "passed": base == shifted,
    }


def delayed_pre_recovery_replay_analysis() -> dict[str, object]:
    spec = PHASE_D_SPEC["delayed_pre_recovery_replay"]
    units = build_balanced_observations(12)
    baseline_events = [
        *_failures(units, float(spec["initial_failure_minute"]), 5),
        *_recoveries(units, float(spec["recovery_minute"])),
        *_failures(units, float(spec["recurrence_minute"]), 2),
    ]
    replay = _failures(
        units,
        float(spec["replay_event_minute"]),
        3,
    )
    now = float(spec["evaluation_minute"])
    baseline = temporal_detector_v2(baseline_events, now)
    with_replay = temporal_detector_v2(
        [*baseline_events, *replay],
        now,
    )

    return {
        "baseline": baseline,
        "withDelayedReplay": with_replay,
        "passed": baseline == with_replay,
    }


def repeated_recovery_idempotence_analysis() -> dict[str, object]:
    spec = PHASE_D_SPEC["repeated_recovery_idempotence"]
    units = build_balanced_observations(12)
    recovery_minutes = [float(value) for value in spec["recovery_minutes"]]

    failures = _failures(units, float(spec["failure_minute"]), 5)
    single = temporal_detector_v2(
        [*failures, *_recoveries(units, recovery_minutes[0])],
        float(spec["evaluation_minute"]),
    )
    repeated_events = [*failures]
    for minute in recovery_minutes:
        repeated_events.extend(_recoveries(units, minute))
    repeated = temporal_detector_v2(
        repeated_events,
        float(spec["evaluation_minute"]),
    )

    return {
        "singleRecovery": single,
        "repeatedRecovery": repeated,
        "passed": single == repeated,
    }


def future_data_isolation_analysis() -> dict[str, object]:
    spec = PHASE_D_SPEC["future_data_isolation"]
    units = build_balanced_observations(12)
    current_count = int(spec["current_units"])
    future_count = int(spec["future_units"])
    current_units = units[:current_count]
    future_units = units[current_count : current_count + future_count]

    now = float(spec["current_minute"])
    current_events = _failures(current_units, now, 2)
    future_events = _failures(
        future_units,
        float(spec["future_minute"]),
        1,
    )

    current_only = temporal_detector_v2(current_events, now)
    with_future = temporal_detector_v2(
        [*current_events, *future_events],
        now,
    )

    score_fields = (
        "confidence",
        "tier",
        "effectiveEvidence",
        "sourceSupport",
        "observationStrength",
        "freshnessFactor",
        "independenceFactor",
        "activeEvidenceUnits",
        "activeFailureEvents",
        "activeEpisodeFailureEvents",
    )
    score_equal = all(
        current_only[field] == with_future[field]
        for field in score_fields
    )
    expected_skew = round(float(spec["future_minute"]) - now, 6)

    return {
        "currentOnly": current_only,
        "withFutureTelemetry": with_future,
        "scoreFieldsEqual": score_equal,
        "passed": (
            score_equal
            and with_future["futureEventCount"] == future_count
            and with_future["maxFutureSkewMinutes"] == expected_skew
        ),
    }


def recurrence_reset_analysis() -> dict[str, object]:
    spec = PHASE_D_SPEC["recurrence_reset"]
    units = build_balanced_observations(12)
    historical = _failures(
        units,
        float(spec["historical_failure_minute"]),
        int(spec["historical_failures_per_unit"]),
    )
    recoveries = _recoveries(units, float(spec["recovery_minute"]))
    fresh = _failures(
        units,
        float(spec["recurrence_minute"]),
        int(spec["fresh_failures_per_unit"]),
    )
    now = float(spec["recurrence_minute"])

    full_timeline = temporal_detector_v2(
        [*historical, *recoveries, *fresh],
        now,
    )
    fresh_only = temporal_detector_v2(fresh, now)

    return {
        "fullTimeline": full_timeline,
        "freshOnly": fresh_only,
        "passed": full_timeline == fresh_only,
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
    analyses = {
        "mixedFingerprint": mixed_fingerprint_analysis(),
        "staleDiverseAmplification": stale_diverse_amplification_analysis(),
        "timeTranslation": time_translation_analysis(),
        "delayedPreRecoveryReplay": delayed_pre_recovery_replay_analysis(),
        "repeatedRecoveryIdempotence": repeated_recovery_idempotence_analysis(),
        "futureDataIsolation": future_data_isolation_analysis(),
        "recurrenceReset": recurrence_reset_analysis(),
    }
    checks = {
        "mixedFingerprintsDoNotMutuallyReinforce": analyses["mixedFingerprint"]["passed"],
        "staleDiverseUnitsCannotEscalateFreshEvidence": analyses["staleDiverseAmplification"]["passed"],
        "timeTranslationInvariant": analyses["timeTranslation"]["passed"],
        "delayedPreRecoveryReplayIgnored": analyses["delayedPreRecoveryReplay"]["passed"],
        "repeatedRecoveryIdempotent": analyses["repeatedRecoveryIdempotence"]["passed"],
        "futureTelemetryDoesNotAlterCurrentConfidence": analyses["futureDataIsolation"]["passed"],
        "postRecoveryRecurrenceStartsFresh": analyses["recurrenceReset"]["passed"],
    }
    commit, dirty = repository_provenance()

    return {
        "lab": "SHIELD Lab #001",
        "phase": "D — post-v2 temporal holdout generalization",
        "runnerVersion": RUNNER_VERSION,
        "scenarioVersion": SCENARIO_VERSION,
        "temporalModelVersion": TEMPORAL_MODEL_VERSION_V2,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "scenarioDigest": stable_digest(PHASE_D_SPEC),
        "temporalConfigDigest": temporal_config_digest_v2(),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "phaseConfig": PHASE_D_SPEC,
        "analyses": analyses,
        "claimChecks": checks,
        "summary": {
            "claimPasses": sum(bool(value) for value in checks.values()),
            "claimCount": len(checks),
            "allPassed": all(checks.values()),
        },
        "interpretation": (
            "Phase D evaluates shield-temporal-evidence-v2 on scenarios created after "
            "the v2 repair was frozen. A failure is valid holdout evidence and must not "
            "be repaired by weakening this suite in place."
        ),
        "limitations": [
            "The holdout scenarios were created after temporal v2 was frozen, but they are not an external or blinded validation dataset.",
            "The suite was designed by inspecting the temporal model's semantics, so it tests generalization to new invariants rather than statistical out-of-sample performance.",
            "Mixed-fingerprint non-reinforcement assumes unrelated fingerprints should not combine into one incident confidence; a production design could instead enforce partitioning before scoring, but that contract must be explicit and tested.",
            "The stale-diversity stress threshold is an experimental robustness criterion rather than a calibrated production threshold.",
            "All scenarios remain deterministic and synthetic; no incident ground truth, source trust, network delay distribution, or remediation action is measured.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    analyses = report["analyses"]
    summary = report["summary"]
    mixed = analyses["mixedFingerprint"]
    stale = analyses["staleDiverseAmplification"]
    lines = [
        "# SHIELD Lab #001 — Phase D Temporal Holdout Summary",
        "",
        f"**Overall:** {'PASS' if summary['allPassed'] else 'FAIL'}  ",
        f"**Temporal model:** `{report['temporalModelVersion']}`  ",
        f"**Repository:** `{report['repositoryCommit']}` (dirty={report['repositoryDirty']})  ",
        f"**Scenario digest:** `{report['scenarioDigest']}`  ",
        f"**Temporal config digest:** `{report['temporalConfigDigest']}`",
        "",
        "## Claim checks",
        "",
    ]
    for name, passed in report["claimChecks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")

    lines.extend(
        [
            "",
            "## New holdout counterexamples",
            "",
            f"- Mixed-fingerprint component A confidence: `{mixed['fingerprintA']['confidence']:.6f}` ({mixed['fingerprintA']['tier']})",
            f"- Mixed-fingerprint component B confidence: `{mixed['fingerprintB']['confidence']:.6f}` ({mixed['fingerprintB']['tier']})",
            f"- Combined mixed-fingerprint confidence: `{mixed['combined']['confidence']:.6f}` ({mixed['combined']['tier']})",
            f"- Mixed-fingerprint confidence amplification: `{mixed['confidenceAmplification']:.6f}`",
            f"- Fresh-only confidence in stale-diversity case: `{stale['freshOnly']['confidence']:.6f}` ({stale['freshOnly']['tier']})",
            f"- With stale diverse units: `{stale['withStaleDiversity']['confidence']:.6f}` ({stale['withStaleDiversity']['tier']})",
            f"- Stale-diversity confidence amplification: `{stale['confidenceAmplification']:.6f}`",
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
        description="Run SHIELD Lab #001 Phase D temporal holdout suite."
    )
    parser.add_argument(
        "--output",
        default="labs/shield_001/results/phase-d-latest.json",
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
