from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from . import phase_c, phase_c2
from .core import stable_digest
from .scoring_v2 import SCORING_VERSION_V2, scoring_digest_v2
from .temporal_v1 import TEMPORAL_MODEL_VERSION, temporal_config_digest
from .temporal_v2 import (
    TEMPORAL_CONFIG_V2,
    TEMPORAL_MODEL_VERSION_V2,
    temporal_config_digest_v2,
    temporal_detector_v2,
)

RUNNER_VERSION = "shield-temporal-v2-validation-runner-v1"
VALIDATION_VERSION = "shield-temporal-v2-frozen-c-c2-validation-v1"


def _phase_c_with_detector(detector):
    with patch.object(phase_c, "temporal_detector", detector):
        return phase_c.build_report()


def _phase_c2_with_detector(detector):
    with patch.object(phase_c2, "temporal_detector", detector):
        return phase_c2.build_report()


def _confidence_regression(v1: dict[str, object], v2: dict[str, object]) -> dict[str, object]:
    v1a = v1["analyses"]
    v2a = v2["analyses"]

    comparisons = {
        "accumulation": (
            [row["confidence"] for row in v1a["accumulation"]["profiles"]],
            [row["confidence"] for row in v2a["accumulation"]["profiles"]],
        ),
        "passiveDecay": (
            [row["confidence"] for row in v1a["passiveDecay"]["profiles"]],
            [row["confidence"] for row in v2a["passiveDecay"]["profiles"]],
        ),
        "partialRecoveryDrop": (
            v1a["partialRecovery"]["confidenceDrop"],
            v2a["partialRecovery"]["confidenceDrop"],
        ),
        "recurrenceConfidence": (
            v1a["recurrence"]["atRecurrence"]["confidence"],
            v2a["recurrence"]["atRecurrence"]["confidence"],
        ),
        "staleVolumeConfidence": (
            v1a["staleVolume"]["profile"]["confidence"],
            v2a["staleVolume"]["profile"]["confidence"],
        ),
    }
    passed = all(left == right for left, right in comparisons.values())
    return {
        "comparisons": {
            name: {"v1": left, "v2": right, "equal": left == right}
            for name, (left, right) in comparisons.items()
        },
        "passed": passed,
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
    phase_c_v1 = phase_c.build_report()
    phase_c2_v1 = phase_c2.build_report()
    phase_c_v2 = _phase_c_with_detector(temporal_detector_v2)
    phase_c2_v2 = _phase_c2_with_detector(temporal_detector_v2)
    confidence_regression = _confidence_regression(phase_c_v1, phase_c_v2)
    commit, dirty = repository_provenance()

    v1_failed_c2 = {
        name for name, passed in phase_c2_v1["claimChecks"].items() if not passed
    }
    expected_v1_failed_c2 = {
        "crossFingerprintRecoveryIsolated",
        "staleHistoryCannotAmplifyFreshEvidence",
        "futureClockSkewIsVisible",
        "timestampTieDoesNotHideContradiction",
    }

    checks = {
        "v1BaselinePreserved": (
            phase_c_v1["summary"]["claimPasses"] == 7
            and phase_c_v1["summary"]["allPassed"]
            and phase_c2_v1["summary"]["claimPasses"] == 3
            and not phase_c2_v1["summary"]["allPassed"]
            and v1_failed_c2 == expected_v1_failed_c2
        ),
        "v2PassesFrozenPhaseC": phase_c_v2["summary"]["allPassed"],
        "v2PassesFrozenPhaseC2": phase_c2_v2["summary"]["allPassed"],
        "phaseCConfidenceRegressionPreserved": confidence_regression["passed"],
        "frozenScenarioIdentityPreserved": (
            phase_c_v1["scenarioDigest"] == phase_c_v2["scenarioDigest"]
            and phase_c2_v1["scenarioDigest"] == phase_c2_v2["scenarioDigest"]
        ),
    }

    return {
        "lab": "SHIELD Lab #001",
        "phase": "Temporal v2 validation against frozen Phase C and C2",
        "runnerVersion": RUNNER_VERSION,
        "validationVersion": VALIDATION_VERSION,
        "temporalV1": TEMPORAL_MODEL_VERSION,
        "temporalV2": TEMPORAL_MODEL_VERSION_V2,
        "baseScoringVersion": SCORING_VERSION_V2,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "phaseCScenarioDigest": phase_c_v1["scenarioDigest"],
        "phaseC2ScenarioDigest": phase_c2_v1["scenarioDigest"],
        "temporalV1ConfigDigest": temporal_config_digest(),
        "temporalV2ConfigDigest": temporal_config_digest_v2(),
        "baseScoringDigest": scoring_digest_v2(),
        "validationDigest": stable_digest(
            {
                "validationVersion": VALIDATION_VERSION,
                "phaseCScenarioDigest": phase_c_v1["scenarioDigest"],
                "phaseC2ScenarioDigest": phase_c2_v1["scenarioDigest"],
                "temporalV2Config": TEMPORAL_CONFIG_V2,
            }
        ),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "results": {
            "phaseCV1": {
                "claimPasses": phase_c_v1["summary"]["claimPasses"],
                "claimCount": phase_c_v1["summary"]["claimCount"],
                "allPassed": phase_c_v1["summary"]["allPassed"],
            },
            "phaseC2V1": {
                "claimPasses": phase_c2_v1["summary"]["claimPasses"],
                "claimCount": phase_c2_v1["summary"]["claimCount"],
                "allPassed": phase_c2_v1["summary"]["allPassed"],
                "failedChecks": sorted(v1_failed_c2),
            },
            "phaseCV2": {
                "claimPasses": phase_c_v2["summary"]["claimPasses"],
                "claimCount": phase_c_v2["summary"]["claimCount"],
                "allPassed": phase_c_v2["summary"]["allPassed"],
            },
            "phaseC2V2": {
                "claimPasses": phase_c2_v2["summary"]["claimPasses"],
                "claimCount": phase_c2_v2["summary"]["claimCount"],
                "allPassed": phase_c2_v2["summary"]["allPassed"],
                "claimChecks": phase_c2_v2["claimChecks"],
                "keyMeasurements": {
                    "crossFingerprintConfidenceDrop": phase_c2_v2["analyses"]["crossFingerprintRecovery"]["confidenceDrop"],
                    "staleHistoryAmplification": phase_c2_v2["analyses"]["mixedStaleHistory"]["confidenceAmplification"],
                    "futureClockSkewVisible": phase_c2_v2["analyses"]["futureClockSkew"]["visibleDifference"],
                    "timestampTieDistinguishable": phase_c2_v2["analyses"]["timestampTie"]["distinguishable"],
                },
            },
            "phaseCConfidenceRegression": confidence_regression,
        },
        "claimChecks": checks,
        "summary": {
            "claimPasses": sum(bool(value) for value in checks.values()),
            "claimCount": len(checks),
            "allPassed": all(checks.values()),
        },
        "interpretation": (
            "Temporal v2 is accepted by this regression only if the frozen temporal-v1 "
            "history is reproduced, all original Phase C checks remain passing, and all "
            "unchanged Phase C2 adversarial checks pass. This is regression-repair "
            "evidence, not independent real-world validation."
        ),
        "limitations": [
            "Temporal v2 was designed after observing the Phase C2 counterexamples.",
            "The current failure episode is defined as failures at an evidence unit's most recent failure timestamp; real telemetry may require a richer episode/window definition.",
            "Future timestamps are surfaced diagnostically but are not rejected, clamped, or quarantined by policy.",
            "Same-timestamp failure/recovery contradictions remain visible, but recovery still wins the confidence tie.",
            "Fingerprint-aware recovery prevents cross-fingerprint suppression but does not prove that fingerprints themselves are causally correct.",
            "All validation scenarios remain deterministic and synthetic; incident precision, recall, source trust, and remediation safety are still unmeasured.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    results = report["results"]
    summary = report["summary"]
    c2v2 = results["phaseC2V2"]
    measurements = c2v2["keyMeasurements"]
    lines = [
        "# SHIELD Lab #001 — Temporal V2 Validation Summary",
        "",
        f"**Overall:** {'PASS' if summary['allPassed'] else 'FAIL'}  ",
        f"**V1:** `{report['temporalV1']}`  ",
        f"**V2:** `{report['temporalV2']}`  ",
        f"**Repository:** `{report['repositoryCommit']}` (dirty={report['repositoryDirty']})  ",
        f"**Phase C digest:** `{report['phaseCScenarioDigest']}`  ",
        f"**Phase C2 digest:** `{report['phaseC2ScenarioDigest']}`",
        "",
        "## Before and after",
        "",
        "| Validation | Temporal v1 | Temporal v2 |",
        "|---|---:|---:|",
        f"| Phase C frozen checks | {results['phaseCV1']['claimPasses']}/{results['phaseCV1']['claimCount']} | {results['phaseCV2']['claimPasses']}/{results['phaseCV2']['claimCount']} |",
        f"| Phase C2 adversarial checks | {results['phaseC2V1']['claimPasses']}/{results['phaseC2V1']['claimCount']} | {results['phaseC2V2']['claimPasses']}/{results['phaseC2V2']['claimCount']} |",
        "",
        "## V2 adversarial measurements",
        "",
        f"- Cross-fingerprint recovery confidence drop: `{measurements['crossFingerprintConfidenceDrop']:.6f}`",
        f"- Mixed stale-history confidence amplification: `{measurements['staleHistoryAmplification']:.6f}`",
        f"- Future clock skew visible: `{measurements['futureClockSkewVisible']}`",
        f"- Same-timestamp contradiction visible: `{measurements['timestampTieDistinguishable']}`",
        "",
        "## Validation checks",
        "",
    ]
    for name, passed in report["claimChecks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")
    lines.extend(["", "## Interpretation", "", report["interpretation"], "", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate SHIELD temporal v2 against frozen Phase C and C2."
    )
    parser.add_argument(
        "--output",
        default="labs/shield_001/results/temporal-v2-validation-latest.json",
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
