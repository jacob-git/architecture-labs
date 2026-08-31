from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .core import Observation, stable_digest
from .scoring_v2 import SCORING_VERSION_V2, scoring_digest_v2
from .temporal_v1 import (
    TEMPORAL_CONFIG,
    TEMPORAL_MODEL_VERSION,
    TemporalEvent,
    temporal_config_digest,
    temporal_detector,
)

RUNNER_VERSION = "shield-phase-c-runner-v1"
SCENARIO_VERSION = "shield-phase-c-scenarios-v1"

PHASE_C_SPEC = {
    "topology": {
        "apps": 12,
        "regions": 3,
        "clusters": 4,
        "gateways": 4,
        "paths": 4,
    },
    "accumulation": {
        "batch_minutes": [0, 5, 10, 15],
        "new_units_per_batch": 3,
        "failures_per_unit": 5,
        "required_final_tier": "high",
    },
    "passive_decay": {
        "failure_events": 60,
        "evaluation_minutes": [0, 30, 60, 90, 120],
        "required_below_high_by_minute": 60,
        "required_low_by_minute": 120,
    },
    "partial_recovery": {
        "recovery_minute": 30,
        "recovered_units": 6,
        "minimum_confidence_drop": 0.20,
    },
    "full_recovery_and_recurrence": {
        "recovery_minute": 45,
        "pre_recurrence_minute": 89,
        "recurrence_minute": 90,
        "required_recurrence_tier": "high",
    },
    "stale_volume": {
        "failure_events": 5000,
        "evaluation_minute": 120,
        "required_tier": "low",
    },
}


def _value(prefix: str, index: int, count: int) -> str:
    return f"{prefix}-{index % count + 1}"


def build_balanced_observations(
    events: int,
    *,
    apps: int = 12,
    regions: int = 3,
    clusters: int = 4,
    gateways: int = 4,
    paths: int = 4,
    session_offset: int = 0,
) -> tuple[Observation, ...]:
    if events < max(apps, regions, clusters, gateways, paths):
        raise ValueError("events must cover the requested topology")

    return tuple(
        Observation(
            app=_value("app", index, apps),
            instance=_value("instance", index, apps),
            host=_value("host", index, apps),
            cluster=_value("cluster", index, clusters),
            region=_value("region", index, regions),
            gateway=_value("gateway", index, gateways),
            path=_value("path", index, paths),
            session=f"session-{session_offset + index + 1}",
        )
        for index in range(events)
    )


def _base_units() -> tuple[Observation, ...]:
    return build_balanced_observations(12)


def accumulation_analysis() -> dict[str, object]:
    events: list[TemporalEvent] = []
    rows: list[dict[str, object]] = []
    units = _base_units()
    spec = PHASE_C_SPEC["accumulation"]

    for batch_index, minute in enumerate(spec["batch_minutes"]):
        start = batch_index * int(spec["new_units_per_batch"])
        stop = start + int(spec["new_units_per_batch"])
        for unit in units[start:stop]:
            for _ in range(int(spec["failures_per_unit"])):
                events.append(TemporalEvent(unit, float(minute), "failure"))

        result = temporal_detector(events, float(minute))
        rows.append(
            {
                "minute": minute,
                "activeEvidenceUnits": result["activeEvidenceUnits"],
                "activeFailureEvents": result["activeFailureEvents"],
                "confidence": result["confidence"],
                "tier": result["tier"],
            }
        )

    strict_increases = sum(
        1
        for lower, higher in zip(rows, rows[1:])
        if higher["confidence"] > lower["confidence"] + 1e-9
    )
    passed = (
        strict_increases == len(rows) - 1
        and rows[-1]["tier"] == spec["required_final_tier"]
    )

    return {
        "profiles": rows,
        "strictIncreaseSteps": strict_increases,
        "passed": passed,
    }


def _sixty_failure_events() -> tuple[TemporalEvent, ...]:
    observations = build_balanced_observations(60)
    return tuple(
        TemporalEvent(observation, 0.0, "failure")
        for observation in observations
    )


def passive_decay_analysis() -> dict[str, object]:
    events = _sixty_failure_events()
    spec = PHASE_C_SPEC["passive_decay"]
    rows = [
        {
            "minute": minute,
            **temporal_detector(events, float(minute)),
        }
        for minute in spec["evaluation_minutes"]
    ]

    strict_decreases = sum(
        1
        for earlier, later in zip(rows, rows[1:])
        if later["confidence"] < earlier["confidence"] - 1e-9
    )
    by_minute = {row["minute"]: row for row in rows}
    below_high = (
        by_minute[spec["required_below_high_by_minute"]]["tier"] != "high"
    )
    low_by_deadline = (
        by_minute[spec["required_low_by_minute"]]["tier"] == "low"
    )

    return {
        "profiles": rows,
        "strictDecreaseSteps": strict_decreases,
        "passed": (
            strict_decreases == len(rows) - 1
            and below_high
            and low_by_deadline
        ),
    }


def partial_recovery_analysis() -> dict[str, object]:
    failures = list(_sixty_failure_events())
    units = _base_units()
    spec = PHASE_C_SPEC["partial_recovery"]
    minute = float(spec["recovery_minute"])

    without_recovery = temporal_detector(failures, minute)
    recoveries = [
        TemporalEvent(unit, minute, "recovery")
        for unit in units[: int(spec["recovered_units"])]
    ]
    with_recovery = temporal_detector([*failures, *recoveries], minute)

    confidence_drop = round(
        without_recovery["confidence"] - with_recovery["confidence"],
        6,
    )

    return {
        "withoutRecovery": without_recovery,
        "withRecovery": with_recovery,
        "confidenceDrop": confidence_drop,
        "minimumRequiredDrop": spec["minimum_confidence_drop"],
        "passed": confidence_drop >= float(spec["minimum_confidence_drop"]),
    }


def recurrence_analysis() -> dict[str, object]:
    failures = list(_sixty_failure_events())
    units = _base_units()
    spec = PHASE_C_SPEC["full_recovery_and_recurrence"]

    recovery_minute = float(spec["recovery_minute"])
    recoveries = [
        TemporalEvent(unit, recovery_minute, "recovery")
        for unit in units
    ]

    recurrence_minute = float(spec["recurrence_minute"])
    recurrent_failures = [
        TemporalEvent(observation, recurrence_minute, "failure")
        for observation in build_balanced_observations(60, session_offset=10_000)
    ]
    timeline = [*failures, *recoveries, *recurrent_failures]

    after_recovery = temporal_detector(timeline, recovery_minute)
    before_recurrence = temporal_detector(
        timeline,
        float(spec["pre_recurrence_minute"]),
    )
    at_recurrence = temporal_detector(timeline, recurrence_minute)

    return {
        "afterRecovery": after_recovery,
        "beforeRecurrence": before_recurrence,
        "atRecurrence": at_recurrence,
        "passed": (
            after_recovery["tier"] == "low"
            and before_recurrence["tier"] == "low"
            and at_recurrence["tier"] == spec["required_recurrence_tier"]
        ),
    }


def stale_volume_analysis() -> dict[str, object]:
    spec = PHASE_C_SPEC["stale_volume"]
    observations = build_balanced_observations(int(spec["failure_events"]))
    events = [
        TemporalEvent(observation, 0.0, "failure")
        for observation in observations
    ]
    result = temporal_detector(events, float(spec["evaluation_minute"]))

    return {
        "profile": result,
        "passed": result["tier"] == spec["required_tier"],
    }


def input_order_analysis() -> dict[str, object]:
    failures = list(_sixty_failure_events())
    recoveries = [
        TemporalEvent(unit, 30.0, "recovery")
        for unit in _base_units()[:6]
    ]
    events = [*failures, *recoveries]
    forward = temporal_detector(events, 30.0)
    reversed_result = temporal_detector(list(reversed(events)), 30.0)

    return {
        "forwardConfidence": forward["confidence"],
        "reversedConfidence": reversed_result["confidence"],
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
    accumulation = accumulation_analysis()
    passive_decay = passive_decay_analysis()
    partial_recovery = partial_recovery_analysis()
    recurrence = recurrence_analysis()
    stale_volume = stale_volume_analysis()
    order_invariance = input_order_analysis()
    commit, dirty = repository_provenance()

    checks = {
        "freshIndependentEvidenceAccumulates": accumulation["passed"],
        "passiveDecayReducesConfidence": passive_decay["passed"],
        "recoverySuppressesPriorFailures": partial_recovery["passed"],
        "recurrenceRebuildsConfidence": recurrence["passed"],
        "futureEvidenceDoesNotLeakBackward": (
            recurrence["beforeRecurrence"]["tier"] == "low"
        ),
        "staleVolumeCannotOverrideDecay": stale_volume["passed"],
        "inputOrderInvariant": order_invariance["passed"],
    }

    return {
        "lab": "SHIELD Lab #001",
        "phase": "C — temporal evidence, recovery, and recurrence",
        "runnerVersion": RUNNER_VERSION,
        "scenarioVersion": SCENARIO_VERSION,
        "temporalModelVersion": TEMPORAL_MODEL_VERSION,
        "baseScoringVersion": SCORING_VERSION_V2,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "scenarioDigest": stable_digest(PHASE_C_SPEC),
        "temporalConfigDigest": temporal_config_digest(),
        "baseScoringDigest": scoring_digest_v2(),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "phaseConfig": PHASE_C_SPEC,
        "temporalConfig": TEMPORAL_CONFIG,
        "analyses": {
            "accumulation": accumulation,
            "passiveDecay": passive_decay,
            "partialRecovery": partial_recovery,
            "recurrence": recurrence,
            "staleVolume": stale_volume,
            "inputOrder": order_invariance,
        },
        "claimChecks": checks,
        "summary": {
            "claimPasses": sum(bool(value) for value in checks.values()),
            "claimCount": len(checks),
            "allPassed": all(checks.values()),
        },
        "interpretation": (
            "Phase C tests a candidate temporal layer on top of the frozen v2 "
            "distribution-aware evidence model. A pass demonstrates only the "
            "predeclared synthetic temporal behaviors; it does not validate the "
            "half-life or recovery semantics for production incidents."
        ),
        "limitations": [
            "The 30-minute half-life is an experimental lab parameter, not a production recommendation.",
            "Recovery is modeled as superseding prior failures for the same app/region/cluster/gateway/path evidence unit.",
            "Freshness decay does not prove causal recovery; it only reduces authority assigned to stale evidence.",
            "The scenarios remain synthetic and do not measure incident precision, recall, or remediation safety.",
            "Contradictory signals, source reliability, clock skew, delayed telemetry, and adversarial timestamps are not modeled yet.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    analyses = report["analyses"]
    summary = report["summary"]
    lines = [
        "# SHIELD Lab #001 — Phase C Summary",
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

    lines.extend(
        [
            "",
            "## Fresh evidence accumulation",
            "",
            "| Minute | Active units | Active failures | Confidence | Tier |",
            "|---:|---:|---:|---:|---|",
        ]
    )
    for row in analyses["accumulation"]["profiles"]:
        lines.append(
            f"| {row['minute']} | {row['activeEvidenceUnits']} | "
            f"{row['activeFailureEvents']} | {row['confidence']:.6f} | {row['tier']} |"
        )

    lines.extend(
        [
            "",
            "## Passive decay",
            "",
            "| Minute | Freshness | Confidence | Tier |",
            "|---:|---:|---:|---|",
        ]
    )
    for row in analyses["passiveDecay"]["profiles"]:
        lines.append(
            f"| {row['minute']} | {row['freshnessFactor']:.6f} | "
            f"{row['confidence']:.6f} | {row['tier']} |"
        )

    recovery = analyses["partialRecovery"]
    recurrence = analyses["recurrence"]
    stale = analyses["staleVolume"]["profile"]
    lines.extend(
        [
            "",
            "## Recovery and recurrence",
            "",
            f"- Partial recovery confidence drop: `{recovery['confidenceDrop']:.6f}` "
            f"(required ≥ `{recovery['minimumRequiredDrop']:.2f}`)",
            f"- Full recovery confidence: `{recurrence['afterRecovery']['confidence']:.6f}`",
            f"- Confidence immediately before recurrence: `{recurrence['beforeRecurrence']['confidence']:.6f}`",
            f"- Confidence at fresh recurrence: `{recurrence['atRecurrence']['confidence']:.6f}`",
            "",
            "## Stale-volume guard",
            "",
            f"A balanced `{PHASE_C_SPEC['stale_volume']['failure_events']:,}`-event historical incident "
            f"evaluated at minute `{PHASE_C_SPEC['stale_volume']['evaluation_minute']}` "
            f"has confidence `{stale['confidence']:.6f}` ({stale['tier']}).",
            "",
            "## Interpretation",
            "",
            report["interpretation"],
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run SHIELD Lab #001 Phase C temporal evidence experiment."
    )
    parser.add_argument(
        "--output",
        default="labs/shield_001/results/phase-c-latest.json",
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
