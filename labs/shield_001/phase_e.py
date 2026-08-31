from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from .core import Observation, SHIELD_HIGH_CONFIDENCE, stable_digest
from .phase_c import build_balanced_observations
from .temporal_v1 import TemporalEvent
from .temporal_v3 import (
    TEMPORAL_MODEL_VERSION_V3,
    temporal_config_digest_v3,
    temporal_detector_v3,
)

RUNNER_VERSION = "shield-phase-e-runner-v1"
CORPUS_VERSION = "shield-phase-e-noisy-ground-truth-v1"

ACCEPTANCE = {
    "classification_threshold": 0.75,
    "minimum_precision": 0.90,
    "minimum_recall": 0.80,
    "maximum_false_positive_rate": 0.10,
    "maximum_brier_score": 0.15,
    "maximum_expected_calibration_error": 0.15,
    "maximum_median_time_to_high_minutes": 15.0,
    "calibration_bins": 5,
}

CASE_SPECS = [
    {"id": "I01", "label": 1, "category": "broad_persistent", "title": "Broad persistent incident: 12 units x 5 failures", "kind": "broad", "units": 12, "failures_per_unit": 5, "evaluation_minute": 0, "incident_onset_minute": 0, "background_noise": True},
    {"id": "I02", "label": 1, "category": "broad_persistent", "title": "Broad persistent incident: 10 units x 5 failures", "kind": "broad", "units": 10, "failures_per_unit": 5, "evaluation_minute": 0, "incident_onset_minute": 0},
    {"id": "I03", "label": 1, "category": "broad_persistent", "title": "Broad persistent incident: 8 units x 5 failures", "kind": "broad", "units": 8, "failures_per_unit": 5, "evaluation_minute": 0, "incident_onset_minute": 0},
    {"id": "I04", "label": 1, "category": "gradual_spread", "title": "Gradual incident spread: 3 failures per unit", "kind": "gradual", "failures_per_unit": 3, "batch_minutes": [0, 5, 10, 15], "evaluation_minute": 15, "incident_onset_minute": 0, "background_noise_minute": 5},
    {"id": "I05", "label": 1, "category": "gradual_spread", "title": "Gradual incident spread: 4 failures per unit", "kind": "gradual", "failures_per_unit": 4, "batch_minutes": [0, 5, 10, 15], "evaluation_minute": 15, "incident_onset_minute": 0, "background_noise_minute": 5},
    {"id": "I06", "label": 1, "category": "gradual_spread", "title": "Gradual incident spread: 5 failures per unit", "kind": "gradual", "failures_per_unit": 5, "batch_minutes": [0, 5, 10, 15], "evaluation_minute": 15, "incident_onset_minute": 0, "background_noise_minute": 5},
    {"id": "I07", "label": 1, "category": "recurrence", "title": "Fresh recurrence after recovered high-volume history", "kind": "recurrence", "units": 12, "historical_failures_per_unit": 50, "recovery_minute": 30, "recurrence_minute": 60, "fresh_failures_per_unit": 2, "evaluation_minute": 60, "incident_onset_minute": 60},
    {"id": "I08", "label": 1, "category": "recurrence", "title": "Ten-unit recurrence after recovery", "kind": "recurrence", "units": 10, "historical_failures_per_unit": 30, "recovery_minute": 30, "recurrence_minute": 60, "fresh_failures_per_unit": 3, "evaluation_minute": 60, "incident_onset_minute": 60},
    {"id": "I09", "label": 1, "category": "recurrence", "title": "Fresh broad incident with stale unrelated fingerprint noise", "kind": "fresh_with_stale_unrelated", "units": 12, "fresh_failures_per_unit": 2, "fresh_minute": 120, "stale_noise_units": 4, "stale_noise_failures_per_unit": 100, "stale_noise_minute": 0, "evaluation_minute": 120, "incident_onset_minute": 120},
    {"id": "I10", "label": 1, "category": "shared_cause_incident", "title": "Real incident with a shared gateway", "kind": "shared_cause", "units": 12, "failures_per_unit": 5, "shared_gateway": True, "shared_path": False, "evaluation_minute": 0, "incident_onset_minute": 0},
    {"id": "I11", "label": 1, "category": "shared_cause_incident", "title": "Real incident with a shared path", "kind": "shared_cause", "units": 12, "failures_per_unit": 5, "shared_gateway": False, "shared_path": True, "evaluation_minute": 0, "incident_onset_minute": 0},
    {"id": "I12", "label": 1, "category": "shared_cause_incident", "title": "Real incident with shared gateway and path", "kind": "shared_cause", "units": 12, "failures_per_unit": 5, "shared_gateway": True, "shared_path": True, "evaluation_minute": 0, "incident_onset_minute": 0},
    {"id": "N01", "label": 0, "category": "localized_noise", "title": "Single-unit retry storm", "kind": "localized_burst", "units": 1, "failures_per_unit": 500, "evaluation_minute": 0},
    {"id": "N02", "label": 0, "category": "localized_noise", "title": "Two-unit correlated burst", "kind": "localized_burst", "units": 2, "failures_per_unit": 200, "evaluation_minute": 0},
    {"id": "N03", "label": 0, "category": "localized_noise", "title": "Three-unit noisy burst", "kind": "localized_burst", "units": 3, "failures_per_unit": 100, "evaluation_minute": 0},
    {"id": "N04", "label": 0, "category": "unrelated_fingerprints", "title": "Two unrelated six-unit medium-confidence fingerprints", "kind": "mixed_fingerprints", "units_per_fingerprint": 6, "failures_per_unit": 5, "evaluation_minute": 0},
    {"id": "N05", "label": 0, "category": "unrelated_fingerprints", "title": "Two unrelated seven-unit fingerprints", "kind": "mixed_fingerprints", "units_per_fingerprint": 7, "failures_per_unit": 5, "evaluation_minute": 0},
    {"id": "N06", "label": 0, "category": "unrelated_fingerprints", "title": "Two unrelated localized high-volume fingerprints", "kind": "mixed_fingerprints", "units_per_fingerprint": 5, "failures_per_unit": 10, "evaluation_minute": 0},
    {"id": "N07", "label": 0, "category": "recovered_or_contradictory", "title": "Broad failure fully recovered before evaluation", "kind": "recovered", "units": 12, "failures_per_unit": 5, "recovery_minute": 20, "evaluation_minute": 30},
    {"id": "N08", "label": 0, "category": "recovered_or_contradictory", "title": "Delayed pre-recovery replay after recovery", "kind": "recovered_replay", "units": 12, "failures_per_unit": 5, "replay_failures_per_unit": 3, "replay_minute": 10, "recovery_minute": 20, "evaluation_minute": 30},
    {"id": "N09", "label": 0, "category": "recovered_or_contradictory", "title": "Same-timestamp failure and recovery contradiction", "kind": "timestamp_tie", "units": 12, "failures_per_unit": 5, "minute": 0, "evaluation_minute": 0},
    {"id": "N10", "label": 0, "category": "stale_or_future", "title": "Stale broad evidence after four half-lives", "kind": "stale", "units": 12, "failures_per_unit": 5, "failure_minute": 0, "evaluation_minute": 120},
    {"id": "N11", "label": 0, "category": "stale_or_future", "title": "Stale high-volume broad evidence after four half-lives", "kind": "stale", "units": 12, "failures_per_unit": 20, "failure_minute": 0, "evaluation_minute": 120},
    {"id": "N12", "label": 0, "category": "stale_or_future", "title": "Future-only telemetry", "kind": "future_only", "units": 12, "failures_per_unit": 5, "future_minute": 105, "evaluation_minute": 100},
]

PHASE_E_SPEC = {
    "corpusVersion": CORPUS_VERSION,
    "acceptance": ACCEPTANCE,
    "caseSpecs": CASE_SPECS,
}


@dataclass(frozen=True)
class GroundTruthCase:
    id: str
    label: int
    category: str
    title: str
    events: tuple[TemporalEvent, ...]
    evaluation_minute: float
    incident_onset_minute: float | None


def _base_units(count: int = 12) -> tuple[Observation, ...]:
    if count < 1 or count > 12:
        raise ValueError("count must be between 1 and 12")
    return build_balanced_observations(12)[:count]


def _with_fingerprint(
    units: tuple[Observation, ...],
    fingerprint: str,
) -> tuple[Observation, ...]:
    return tuple(replace(unit, fingerprint=fingerprint) for unit in units)


def _with_shared_cause(
    units: tuple[Observation, ...],
    *,
    shared_gateway: bool,
    shared_path: bool,
) -> tuple[Observation, ...]:
    return tuple(
        replace(
            unit,
            gateway="gateway-shared" if shared_gateway else unit.gateway,
            path="path-shared" if shared_path else unit.path,
        )
        for unit in units
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


def _background_noise(minute: float, fingerprint: str) -> list[TemporalEvent]:
    unit = _with_fingerprint(_base_units(1), fingerprint)
    return _failures(unit, minute, 50)


def _build_events(spec: dict[str, object]) -> tuple[TemporalEvent, ...]:
    kind = str(spec["kind"])
    events: list[TemporalEvent] = []

    if kind in {"broad", "localized_burst"}:
        units = _base_units(int(spec["units"]))
        events.extend(_failures(units, 0.0, int(spec["failures_per_unit"])))
        if bool(spec.get("background_noise", False)):
            events.extend(_background_noise(0.0, f"noise-{spec['id']}"))

    elif kind == "gradual":
        units = _base_units(12)
        per_unit = int(spec["failures_per_unit"])
        for batch_index, minute in enumerate(spec["batch_minutes"]):
            start = batch_index * 3
            events.extend(
                _failures(units[start : start + 3], float(minute), per_unit)
            )
        if "background_noise_minute" in spec:
            events.extend(
                _background_noise(
                    float(spec["background_noise_minute"]),
                    f"noise-{spec['id']}",
                )
            )

    elif kind == "recurrence":
        units = _base_units(int(spec["units"]))
        events.extend(
            _failures(units, 0.0, int(spec["historical_failures_per_unit"]))
        )
        events.extend(_recoveries(units, float(spec["recovery_minute"])))
        events.extend(
            _failures(
                units,
                float(spec["recurrence_minute"]),
                int(spec["fresh_failures_per_unit"]),
            )
        )

    elif kind == "fresh_with_stale_unrelated":
        fresh_units = _base_units(int(spec["units"]))
        stale_units = _with_fingerprint(
            _base_units(int(spec["stale_noise_units"])),
            "stale-background-noise",
        )
        events.extend(
            _failures(
                stale_units,
                float(spec["stale_noise_minute"]),
                int(spec["stale_noise_failures_per_unit"]),
            )
        )
        events.extend(
            _failures(
                fresh_units,
                float(spec["fresh_minute"]),
                int(spec["fresh_failures_per_unit"]),
            )
        )

    elif kind == "shared_cause":
        units = _with_shared_cause(
            _base_units(int(spec["units"])),
            shared_gateway=bool(spec["shared_gateway"]),
            shared_path=bool(spec["shared_path"]),
        )
        events.extend(_failures(units, 0.0, int(spec["failures_per_unit"])))

    elif kind == "mixed_fingerprints":
        count = int(spec["units_per_fingerprint"])
        all_units = _base_units(12)
        units_a = _with_fingerprint(all_units[:count], "dependency-a-timeout")
        units_b = _with_fingerprint(all_units[-count:], "dependency-b-timeout")
        events.extend(_failures(units_a, 0.0, int(spec["failures_per_unit"])))
        events.extend(_failures(units_b, 0.0, int(spec["failures_per_unit"])))

    elif kind == "recovered":
        units = _base_units(int(spec["units"]))
        events.extend(_failures(units, 0.0, int(spec["failures_per_unit"])))
        events.extend(_recoveries(units, float(spec["recovery_minute"])))

    elif kind == "recovered_replay":
        units = _base_units(int(spec["units"]))
        events.extend(_failures(units, 0.0, int(spec["failures_per_unit"])))
        events.extend(
            _failures(
                units,
                float(spec["replay_minute"]),
                int(spec["replay_failures_per_unit"]),
            )
        )
        events.extend(_recoveries(units, float(spec["recovery_minute"])))

    elif kind == "timestamp_tie":
        units = _base_units(int(spec["units"]))
        minute = float(spec["minute"])
        events.extend(_failures(units, minute, int(spec["failures_per_unit"])))
        events.extend(_recoveries(units, minute))

    elif kind == "stale":
        units = _base_units(int(spec["units"]))
        events.extend(
            _failures(
                units,
                float(spec["failure_minute"]),
                int(spec["failures_per_unit"]),
            )
        )

    elif kind == "future_only":
        units = _base_units(int(spec["units"]))
        events.extend(
            _failures(
                units,
                float(spec["future_minute"]),
                int(spec["failures_per_unit"]),
            )
        )

    else:
        raise ValueError(f"unknown Phase E case kind: {kind}")

    return tuple(events)


def build_cases() -> tuple[GroundTruthCase, ...]:
    cases = []
    for spec in CASE_SPECS:
        onset = spec.get("incident_onset_minute")
        cases.append(
            GroundTruthCase(
                id=str(spec["id"]),
                label=int(spec["label"]),
                category=str(spec["category"]),
                title=str(spec["title"]),
                events=_build_events(spec),
                evaluation_minute=float(spec["evaluation_minute"]),
                incident_onset_minute=(float(onset) if onset is not None else None),
            )
        )
    return tuple(cases)


def _time_to_high(case: GroundTruthCase) -> float | None:
    if case.label != 1 or case.incident_onset_minute is None:
        return None

    minute = case.incident_onset_minute
    threshold = float(ACCEPTANCE["classification_threshold"])
    while minute <= case.evaluation_minute + 1e-9:
        result = temporal_detector_v3(case.events, minute)
        if float(result["confidence"]) >= threshold:
            return round(minute - case.incident_onset_minute, 6)
        minute += 5.0
    return None


def evaluate_case(case: GroundTruthCase) -> dict[str, object]:
    result = temporal_detector_v3(case.events, case.evaluation_minute)
    confidence = float(result["confidence"])
    threshold = float(ACCEPTANCE["classification_threshold"])
    predicted = confidence >= threshold
    expected = bool(case.label)

    return {
        "caseId": case.id,
        "title": case.title,
        "category": case.category,
        "label": case.label,
        "groundTruth": "incident" if expected else "nonincident",
        "evaluationMinute": case.evaluation_minute,
        "incidentOnsetMinute": case.incident_onset_minute,
        "confidence": confidence,
        "tier": result["tier"],
        "selectedFingerprint": result["selectedFingerprint"],
        "predictedIncident": predicted,
        "correct": predicted == expected,
        "timeToHighMinutes": _time_to_high(case),
        "diagnostics": {
            "futureEventCount": result["futureEventCount"],
            "timestampConflictUnits": result["timestampConflictUnits"],
            "activeFingerprintCount": result["activeFingerprintCount"],
        },
    }


def _classification_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    tp = sum(row["label"] == 1 and row["predictedIncident"] for row in rows)
    fp = sum(row["label"] == 0 and row["predictedIncident"] for row in rows)
    tn = sum(row["label"] == 0 and not row["predictedIncident"] for row in rows)
    fn = sum(row["label"] == 1 and not row["predictedIncident"] for row in rows)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    false_positive_rate = fp / (fp + tn) if fp + tn else 0.0
    accuracy = (tp + tn) / len(rows) if rows else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "truePositive": tp,
        "falsePositive": fp,
        "trueNegative": tn,
        "falseNegative": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "falsePositiveRate": round(false_positive_rate, 6),
        "accuracy": round(accuracy, 6),
        "f1": round(f1, 6),
    }


def _calibration_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    if not rows:
        return {"brierScore": 0.0, "expectedCalibrationError": 0.0, "bins": []}

    brier = sum(
        (float(row["confidence"]) - int(row["label"])) ** 2
        for row in rows
    ) / len(rows)

    bin_count = int(ACCEPTANCE["calibration_bins"])
    bins: list[dict[str, object]] = []
    ece = 0.0

    for index in range(bin_count):
        lower = index / bin_count
        upper = (index + 1) / bin_count
        bucket = [
            row
            for row in rows
            if (
                lower <= float(row["confidence"]) < upper
                or (index == bin_count - 1 and float(row["confidence"]) == 1.0)
            )
        ]
        if not bucket:
            continue
        mean_confidence = sum(float(row["confidence"]) for row in bucket) / len(bucket)
        incident_rate = sum(int(row["label"]) for row in bucket) / len(bucket)
        gap = abs(mean_confidence - incident_rate)
        weight = len(bucket) / len(rows)
        ece += weight * gap
        bins.append(
            {
                "lower": round(lower, 6),
                "upper": round(upper, 6),
                "count": len(bucket),
                "meanConfidence": round(mean_confidence, 6),
                "incidentRate": round(incident_rate, 6),
                "absoluteGap": round(gap, 6),
            }
        )

    return {
        "brierScore": round(brier, 6),
        "expectedCalibrationError": round(ece, 6),
        "bins": bins,
        "interpretationBoundary": (
            "SHIELD confidence is not yet established as a calibrated incident "
            "probability. Brier and ECE are exploratory score-calibration diagnostics."
        ),
    }


def _time_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    detected_times = [
        float(row["timeToHighMinutes"])
        for row in rows
        if row["label"] == 1 and row["timeToHighMinutes"] is not None
    ]
    missed = [
        str(row["caseId"])
        for row in rows
        if row["label"] == 1 and row["timeToHighMinutes"] is None
    ]
    return {
        "detectedIncidentCount": len(detected_times),
        "missedIncidentCount": len(missed),
        "missedCaseIds": missed,
        "medianTimeToHighMinutes": (
            round(statistics.median(detected_times), 6) if detected_times else None
        ),
        "maximumTimeToHighMinutes": (
            round(max(detected_times), 6) if detected_times else None
        ),
    }


def _category_metrics(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    categories = sorted({str(row["category"]) for row in rows})
    result = []
    for category in categories:
        bucket = [row for row in rows if row["category"] == category]
        correct = sum(bool(row["correct"]) for row in bucket)
        result.append(
            {
                "category": category,
                "cases": len(bucket),
                "correct": correct,
                "accuracy": round(correct / len(bucket), 6),
                "caseIds": [row["caseId"] for row in bucket],
            }
        )
    return result


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
    if float(ACCEPTANCE["classification_threshold"]) != SHIELD_HIGH_CONFIDENCE:
        raise ValueError("Phase E classification threshold must equal SHIELD high tier")

    cases = build_cases()
    rows = [evaluate_case(case) for case in cases]
    classification = _classification_metrics(rows)
    calibration = _calibration_metrics(rows)
    timing = _time_metrics(rows)
    incident_count = sum(case.label == 1 for case in cases)
    nonincident_count = len(cases) - incident_count

    checks = {
        "balancedFrozenCorpus": len(cases) == 24 and incident_count == 12 and nonincident_count == 12,
        "precisionAtLeast90Percent": float(classification["precision"]) >= float(ACCEPTANCE["minimum_precision"]),
        "recallAtLeast80Percent": float(classification["recall"]) >= float(ACCEPTANCE["minimum_recall"]),
        "falsePositiveRateAtMost10Percent": float(classification["falsePositiveRate"]) <= float(ACCEPTANCE["maximum_false_positive_rate"]),
        "brierScoreAtMost015": float(calibration["brierScore"]) <= float(ACCEPTANCE["maximum_brier_score"]),
        "expectedCalibrationErrorAtMost015": float(calibration["expectedCalibrationError"]) <= float(ACCEPTANCE["maximum_expected_calibration_error"]),
        "medianTimeToHighAtMost15Minutes": timing["medianTimeToHighMinutes"] is not None and float(timing["medianTimeToHighMinutes"]) <= float(ACCEPTANCE["maximum_median_time_to_high_minutes"]),
    }
    commit, dirty = repository_provenance()

    return {
        "lab": "SHIELD Lab #001",
        "phase": "E — noisy synthetic ground truth and calibration",
        "runnerVersion": RUNNER_VERSION,
        "corpusVersion": CORPUS_VERSION,
        "temporalModelVersion": TEMPORAL_MODEL_VERSION_V3,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "corpusDigest": stable_digest(PHASE_E_SPEC),
        "temporalConfigDigest": temporal_config_digest_v3(),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "phaseConfig": PHASE_E_SPEC,
        "cases": rows,
        "metrics": {
            "classification": classification,
            "calibration": calibration,
            "timeToConfidence": timing,
            "categories": _category_metrics(rows),
        },
        "claimChecks": checks,
        "summary": {
            "claimPasses": sum(bool(value) for value in checks.values()),
            "claimCount": len(checks),
            "allPassed": all(checks.values()),
        },
        "interpretation": (
            "Phase E is the first SHIELD lab phase with explicit synthetic incident "
            "and non-incident labels. At the frozen high-confidence boundary, it tests "
            "whether temporal v3 can separate corroborated incidents from noisy, stale, "
            "recovered, contradictory, future-dated, and unrelated evidence. A miss on "
            "a true shared-cause incident is a valid false negative for this detector "
            "experiment even though SHIELD intentionally separates confidence from severity."
        ),
        "limitations": [
            "Ground truth is synthetic and authored in the same repository; this is not external, blinded, or production validation.",
            "The corpus is balanced 12/12, so prevalence-sensitive production metrics cannot be inferred from these rates.",
            "The 0.75 classification boundary is the existing SHIELD high-confidence tier, not a newly optimized Phase E threshold.",
            "SHIELD confidence is not established as a calibrated probability; Brier score and ECE are exploratory diagnostics.",
            "Shared-cause incident cases intentionally test recall when a real incident has low evidence diversity; low confidence may be correct epistemically even while it is a detector false negative against the incident label.",
            "No severity, blast radius, remediation authority, source reliability, cryptographic telemetry integrity, or real trace replay is modeled.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    metrics = report["metrics"]
    classification = metrics["classification"]
    calibration = metrics["calibration"]
    timing = metrics["timeToConfidence"]
    summary = report["summary"]

    lines = [
        "# SHIELD Lab #001 — Phase E Summary",
        "",
        f"**Overall:** {'PASS' if summary['allPassed'] else 'FAIL'}  ",
        f"**Temporal model:** `{report['temporalModelVersion']}`  ",
        f"**Repository:** `{report['repositoryCommit']}` (dirty={report['repositoryDirty']})  ",
        f"**Corpus:** `{report['corpusVersion']}`  ",
        f"**Corpus digest:** `{report['corpusDigest']}`",
        "",
        "## Classification at the frozen high-confidence boundary",
        "",
        "| TP | FP | TN | FN | Precision | Recall | FPR | F1 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {classification['truePositive']} | {classification['falsePositive']} | "
            f"{classification['trueNegative']} | {classification['falseNegative']} | "
            f"{classification['precision']:.6f} | {classification['recall']:.6f} | "
            f"{classification['falsePositiveRate']:.6f} | {classification['f1']:.6f} |"
        ),
        "",
        "## Calibration diagnostics",
        "",
        f"- Brier score: `{calibration['brierScore']:.6f}`",
        f"- Expected calibration error: `{calibration['expectedCalibrationError']:.6f}`",
        f"- Median time to high among detected incidents: `{timing['medianTimeToHighMinutes']}` minutes",
        f"- Missed incident cases: `{', '.join(timing['missedCaseIds']) or 'none'}`",
        "",
        "## Claim checks",
        "",
    ]
    for name, passed in report["claimChecks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")

    lines.extend(
        [
            "",
            "## Case results",
            "",
            "| Case | Ground truth | Category | Confidence | Tier | Predicted | Correct | Time to high |",
            "|---|---|---|---:|---|---|---|---:|",
        ]
    )
    for row in report["cases"]:
        time_value = "—" if row["timeToHighMinutes"] is None else f"{float(row['timeToHighMinutes']):.1f}"
        lines.append(
            f"| {row['caseId']} | {row['groundTruth']} | {row['category']} | "
            f"{row['confidence']:.6f} | {row['tier']} | "
            f"{'incident' if row['predictedIncident'] else 'nonincident'} | "
            f"{'yes' if row['correct'] else 'no'} | {time_value} |"
        )

    lines.extend(["", "## Interpretation", "", report["interpretation"], "", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run SHIELD Phase E noisy ground-truth evaluation."
    )
    parser.add_argument(
        "--output",
        default="labs/shield_001/results/phase-e-latest.json",
        help="JSON result path.",
    )
    parser.add_argument(
        "--summary-output",
        help="Markdown summary path. Defaults beside the JSON result.",
    )
    args = parser.parse_args()

    report = build_report()
    output = Path(args.output)
    summary_output = Path(args.summary_output) if args.summary_output else output.with_suffix(".summary.md")
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
