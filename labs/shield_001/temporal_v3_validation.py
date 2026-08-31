from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from . import phase_c, phase_c2, phase_d
from .core import stable_digest
from .scoring_v2 import SCORING_VERSION_V2, scoring_digest_v2
from .temporal_v2 import (
    TEMPORAL_MODEL_VERSION_V2,
    temporal_config_digest_v2,
    temporal_detector_v2,
)
from .temporal_v3 import (
    TEMPORAL_CONFIG_V3,
    TEMPORAL_MODEL_VERSION_V3,
    temporal_config_digest_v3,
    temporal_detector_v3,
)

RUNNER_VERSION = "shield-temporal-v3-validation-runner-v1"
VALIDATION_VERSION = "shield-temporal-v3-frozen-c-c2-d-validation-v1"


def _phase_c_with_detector(detector):
    with patch.object(phase_c, "temporal_detector", detector):
        return phase_c.build_report()


def _phase_c2_with_detector(detector):
    with patch.object(phase_c2, "temporal_detector", detector):
        return phase_c2.build_report()


def _phase_d_with_detector(detector):
    with patch.object(phase_d, "temporal_detector_v2", detector):
        return phase_d.build_report()


def _phase_c_confidence_regression(
    v2: dict[str, object],
    v3: dict[str, object],
) -> dict[str, object]:
    v2a = v2["analyses"]
    v3a = v3["analyses"]
    comparisons = {
        "accumulation": (
            [row["confidence"] for row in v2a["accumulation"]["profiles"]],
            [row["confidence"] for row in v3a["accumulation"]["profiles"]],
        ),
        "passiveDecay": (
            [row["confidence"] for row in v2a["passiveDecay"]["profiles"]],
            [row["confidence"] for row in v3a["passiveDecay"]["profiles"]],
        ),
        "partialRecoveryDrop": (
            v2a["partialRecovery"]["confidenceDrop"],
            v3a["partialRecovery"]["confidenceDrop"],
        ),
        "recurrenceConfidence": (
            v2a["recurrence"]["atRecurrence"]["confidence"],
            v3a["recurrence"]["atRecurrence"]["confidence"],
        ),
        "staleVolumeConfidence": (
            v2a["staleVolume"]["profile"]["confidence"],
            v3a["staleVolume"]["profile"]["confidence"],
        ),
    }
    return {
        "comparisons": {
            name: {
                "v2": left,
                "v3": right,
                "equal": left == right,
            }
            for name, (left, right) in comparisons.items()
        },
        "passed": all(left == right for left, right in comparisons.values()),
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
    phase_c_v2 = _phase_c_with_detector(temporal_detector_v2)
    phase_c2_v2 = _phase_c2_with_detector(temporal_detector_v2)
    phase_d_v2 = phase_d.build_report()

    phase_c_v3 = _phase_c_with_detector(temporal_detector_v3)
    phase_c2_v3 = _phase_c2_with_detector(temporal_detector_v3)
    phase_d_v3 = _phase_d_with_detector(temporal_detector_v3)

    confidence_regression = _phase_c_confidence_regression(
        phase_c_v2,
        phase_c_v3,
    )
    commit, dirty = repository_provenance()

    v2_failed_d = {
        name
        for name, passed in phase_d_v2["claimChecks"].items()
        if not passed
    }
    expected_v2_failed_d = {
        "mixedFingerprintsDoNotMutuallyReinforce",
        "staleDiverseUnitsCannotEscalateFreshEvidence",
    }

    checks = {
        "v2BaselinePreserved": (
            phase_c_v2["summary"]["claimPasses"] == 7
            and phase_c_v2["summary"]["allPassed"]
            and phase_c2_v2["summary"]["claimPasses"] == 7
            and phase_c2_v2["summary"]["allPassed"]
            and phase_d_v2["summary"]["claimPasses"] == 5
            and not phase_d_v2["summary"]["allPassed"]
            and v2_failed_d == expected_v2_failed_d
        ),
        "v3PassesFrozenPhaseC": phase_c_v3["summary"]["allPassed"],
        "v3PassesFrozenPhaseC2": phase_c2_v3["summary"]["allPassed"],
        "v3PassesFrozenPhaseD": phase_d_v3["summary"]["allPassed"],
        "phaseCConfidenceRegressionPreserved": confidence_regression["passed"],
        "frozenScenarioIdentityPreserved": (
            phase_c_v2["scenarioDigest"] == phase_c_v3["scenarioDigest"]
            and phase_c2_v2["scenarioDigest"] == phase_c2_v3["scenarioDigest"]
            and phase_d_v2["scenarioDigest"] == phase_d_v3["scenarioDigest"]
        ),
    }

    d_v2 = phase_d_v2["analyses"]
    d_v3 = phase_d_v3["analyses"]

    return {
        "lab": "SHIELD Lab #001",
        "phase": "Temporal v3 validation against frozen Phase C, C2, and D",
        "runnerVersion": RUNNER_VERSION,
        "validationVersion": VALIDATION_VERSION,
        "temporalV2": TEMPORAL_MODEL_VERSION_V2,
        "temporalV3": TEMPORAL_MODEL_VERSION_V3,
        "baseScoringVersion": SCORING_VERSION_V2,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "phaseCScenarioDigest": phase_c_v2["scenarioDigest"],
        "phaseC2ScenarioDigest": phase_c2_v2["scenarioDigest"],
        "phaseDScenarioDigest": phase_d_v2["scenarioDigest"],
        "temporalV2ConfigDigest": temporal_config_digest_v2(),
        "temporalV3ConfigDigest": temporal_config_digest_v3(),
        "baseScoringDigest": scoring_digest_v2(),
        "validationDigest": stable_digest(
            {
                "validationVersion": VALIDATION_VERSION,
                "phaseCScenarioDigest": phase_c_v2["scenarioDigest"],
                "phaseC2ScenarioDigest": phase_c2_v2["scenarioDigest"],
                "phaseDScenarioDigest": phase_d_v2["scenarioDigest"],
                "temporalV3Config": TEMPORAL_CONFIG_V3,
            }
        ),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "results": {
            "phaseCV2": {
                "claimPasses": phase_c_v2["summary"]["claimPasses"],
                "claimCount": phase_c_v2["summary"]["claimCount"],
                "allPassed": phase_c_v2["summary"]["allPassed"],
            },
            "phaseC2V2": {
                "claimPasses": phase_c2_v2["summary"]["claimPasses"],
                "claimCount": phase_c2_v2["summary"]["claimCount"],
                "allPassed": phase_c2_v2["summary"]["allPassed"],
            },
            "phaseDV2": {
                "claimPasses": phase_d_v2["summary"]["claimPasses"],
                "claimCount": phase_d_v2["summary"]["claimCount"],
                "allPassed": phase_d_v2["summary"]["allPassed"],
                "failedChecks": sorted(v2_failed_d),
            },
            "phaseCV3": {
                "claimPasses": phase_c_v3["summary"]["claimPasses"],
                "claimCount": phase_c_v3["summary"]["claimCount"],
                "allPassed": phase_c_v3["summary"]["allPassed"],
            },
            "phaseC2V3": {
                "claimPasses": phase_c2_v3["summary"]["claimPasses"],
                "claimCount": phase_c2_v3["summary"]["claimCount"],
                "allPassed": phase_c2_v3["summary"]["allPassed"],
            },
            "phaseDV3": {
                "claimPasses": phase_d_v3["summary"]["claimPasses"],
                "claimCount": phase_d_v3["summary"]["claimCount"],
                "allPassed": phase_d_v3["summary"]["allPassed"],
                "claimChecks": phase_d_v3["claimChecks"],
            },
            "phaseCConfidenceRegression": confidence_regression,
            "phaseDKeyMeasurements": {
                "mixedFingerprint": {
                    "v2CombinedConfidence": d_v2["mixedFingerprint"]["combined"]["confidence"],
                    "v3CombinedConfidence": d_v3["mixedFingerprint"]["combined"]["confidence"],
                    "v3ComponentMax": max(
                        d_v3["mixedFingerprint"]["fingerprintA"]["confidence"],
                        d_v3["mixedFingerprint"]["fingerprintB"]["confidence"],
                    ),
                    "v2Amplification": d_v2["mixedFingerprint"]["confidenceAmplification"],
                    "v3Amplification": d_v3["mixedFingerprint"]["confidenceAmplification"],
                },
                "staleDiverse": {
                    "v2FreshOnlyConfidence": d_v2["staleDiverseAmplification"]["freshOnly"]["confidence"],
                    "v2WithStaleConfidence": d_v2["staleDiverseAmplification"]["withStaleDiversity"]["confidence"],
                    "v3FreshOnlyConfidence": d_v3["staleDiverseAmplification"]["freshOnly"]["confidence"],
                    "v3WithStaleConfidence": d_v3["staleDiverseAmplification"]["withStaleDiversity"]["confidence"],
                    "v2Amplification": d_v2["staleDiverseAmplification"]["confidenceAmplification"],
                    "v3Amplification": d_v3["staleDiverseAmplification"]["confidenceAmplification"],
                },
            },
        },
        "claimChecks": checks,
        "summary": {
            "claimPasses": sum(bool(value) for value in checks.values()),
            "claimCount": len(checks),
            "allPassed": all(checks.values()),
        },
        "interpretation": (
            "Temporal v3 is accepted by this regression only if temporal v2's "
            "previously measured history is reproduced, the unchanged Phase C "
            "and C2 suites remain passing, and all seven frozen Phase D holdout "
            "checks pass without modifying temporal v2 or the Phase D criteria. "
            "Because v3 was designed after observing the Phase D failures, this "
            "is regression-repair evidence rather than a new independent holdout."
        ),
        "limitations": [
            "Temporal v3 was designed after observing the two Phase D holdout failures.",
            "Selecting the maximum per-fingerprint confidence assumes fingerprints define incident evidence partitions; real deployments need an explicit fingerprinting and incident-grouping contract.",
            "Episode-volume-weighted freshness prevents old high-volume units from dominating the freshness factor, but it is still an experimental aggregation rule.",
            "A stale fingerprint can remain separately visible even when it no longer reinforces a fresher fingerprint; downstream incident aggregation is not modeled.",
            "All current suites are deterministic and synthetic; source trust, noisy incident ground truth, network-delay distributions, and remediation safety remain unmeasured.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    results = report["results"]
    summary = report["summary"]
    mixed = results["phaseDKeyMeasurements"]["mixedFingerprint"]
    stale = results["phaseDKeyMeasurements"]["staleDiverse"]

    lines = [
        "# SHIELD Lab #001 — Temporal V3 Validation Summary",
        "",
        f"**Overall:** {'PASS' if summary['allPassed'] else 'FAIL'}  ",
        f"**V2:** `{report['temporalV2']}`  ",
        f"**V3:** `{report['temporalV3']}`  ",
        f"**Repository:** `{report['repositoryCommit']}` (dirty={report['repositoryDirty']})  ",
        f"**Phase C digest:** `{report['phaseCScenarioDigest']}`  ",
        f"**Phase C2 digest:** `{report['phaseC2ScenarioDigest']}`  ",
        f"**Phase D digest:** `{report['phaseDScenarioDigest']}`",
        "",
        "## Before and after",
        "",
        "| Validation | Temporal v2 | Temporal v3 |",
        "|---|---:|---:|",
        f"| Phase C | {results['phaseCV2']['claimPasses']}/{results['phaseCV2']['claimCount']} | {results['phaseCV3']['claimPasses']}/{results['phaseCV3']['claimCount']} |",
        f"| Phase C2 | {results['phaseC2V2']['claimPasses']}/{results['phaseC2V2']['claimCount']} | {results['phaseC2V3']['claimPasses']}/{results['phaseC2V3']['claimCount']} |",
        f"| Phase D holdout | {results['phaseDV2']['claimPasses']}/{results['phaseDV2']['claimCount']} | {results['phaseDV3']['claimPasses']}/{results['phaseDV3']['claimCount']} |",
        "",
        "## Phase D repairs",
        "",
        f"- Mixed-fingerprint combined confidence: `{mixed['v2CombinedConfidence']:.6f}` → `{mixed['v3CombinedConfidence']:.6f}`",
        f"- Mixed-fingerprint amplification: `{mixed['v2Amplification']:.6f}` → `{mixed['v3Amplification']:.6f}`",
        f"- Stale-diverse confidence: `{stale['v2WithStaleConfidence']:.6f}` → `{stale['v3WithStaleConfidence']:.6f}`",
        f"- Stale-diverse amplification: `{stale['v2Amplification']:.6f}` → `{stale['v3Amplification']:.6f}`",
        "",
        "## Validation checks",
        "",
    ]
    for name, passed in report["claimChecks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")

    lines.extend(
        [
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
        description=(
            "Validate SHIELD temporal v3 against frozen Phase C, C2, and D."
        )
    )
    parser.add_argument(
        "--output",
        default=(
            "labs/shield_001/results/"
            "temporal-v3-validation-latest.json"
        ),
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
    output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    summary_output.write_text(
        render_summary(report),
        encoding="utf-8",
    )

    print(render_summary(report))
    print(f"JSON:    {output}")
    print(f"Summary: {summary_output}")
    raise SystemExit(0 if report["summary"]["allPassed"] else 2)


if __name__ == "__main__":
    main()
