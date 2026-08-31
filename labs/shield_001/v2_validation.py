from __future__ import annotations

import argparse
import itertools
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

from .core import (
    SCORING_VERSION,
    build_scenarios,
    distinct_reporter_detector,
    evaluate_scenario,
    raw_threshold_detector,
    scoring_digest,
    stable_digest,
)
from .phase_b import (
    APP_LEVELS,
    CLUSTER_LEVELS,
    CONCENTRATION_LEVELS,
    EVENT_LEVELS,
    GATEWAY_LEVELS,
    MAX_POST_SATURATION_GAIN,
    MIN_CONCENTRATION_DROP,
    PATH_LEVELS,
    REGION_LEVELS,
    SWEEP_CONFIG,
    SWEEP_VERSION,
    adversarial_ranking_analysis,
    build_observations,
    concentration_analysis,
    matrix_profiles,
    monotonicity_analysis,
    repository_provenance,
    volume_saturation_analysis,
)
from .scoring_v2 import (
    SCORING_VERSION_V2,
    SHIELD_CONFIG_V2,
    scoring_digest_v2,
    shield_detector_v2,
)

RUNNER_VERSION = "shield-v2-validation-runner-v1"


def evaluate_phase_a_v2() -> dict[str, object]:
    results: list[dict[str, object]] = []
    for scenario in build_scenarios():
        raw = raw_threshold_detector(scenario.observations)
        distinct = distinct_reporter_detector(scenario.observations)
        shield = shield_detector_v2(scenario.observations)
        checks = {
            "raw": raw["escalated"] is scenario.expected["raw"],
            "distinct": distinct["escalated"] is scenario.expected["distinct"],
            "shieldTier": shield["tier"] == scenario.expected["shield_tier"],
        }
        results.append(
            {
                "scenarioId": scenario.id,
                "expected": scenario.expected,
                "rawThreshold": raw,
                "distinctReporter": distinct,
                "shield": shield,
                "checks": checks,
                "passed": all(checks.values()),
            }
        )

    return {
        "scenarioCount": len(results),
        "scenarioPasses": sum(result["passed"] for result in results),
        "allPassed": all(result["passed"] for result in results),
        "results": results,
    }


def evaluate_phase_a_v1() -> dict[str, object]:
    results = [evaluate_scenario(scenario) for scenario in build_scenarios()]
    return {
        "scenarioCount": len(results),
        "scenarioPasses": sum(result["passed"] for result in results),
        "allPassed": all(result["passed"] for result in results),
        "results": results,
    }


def evaluate_profile_v2(**profile: object) -> dict[str, object]:
    observations = build_observations(**profile)
    shield = shield_detector_v2(observations)
    return {
        "profile": profile,
        "confidence": shield["confidence"],
        "tier": shield["tier"],
        "independenceFactor": shield["independenceFactor"],
        "effectiveCounts": shield["effectiveCounts"],
        "concentration": shield["concentration"],
    }


def matrix_profiles_v2() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for events, apps, regions, clusters, gateways, paths in itertools.product(
        EVENT_LEVELS,
        APP_LEVELS,
        REGION_LEVELS,
        CLUSTER_LEVELS,
        GATEWAY_LEVELS,
        PATH_LEVELS,
    ):
        if events < max(apps, regions, clusters, gateways, paths):
            continue
        rows.append(
            evaluate_profile_v2(
                events=events,
                apps=apps,
                regions=regions,
                clusters=clusters,
                gateways=gateways,
                paths=paths,
            )
        )
    return rows


def concentration_analysis_v2() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for ratio in CONCENTRATION_LEVELS:
        row = evaluate_profile_v2(
            events=500,
            apps=20,
            regions=3,
            clusters=4,
            gateways=4,
            paths=4,
            gateway_concentration=ratio,
            path_concentration=ratio,
        )
        row["requestedConcentration"] = ratio
        rows.append(row)

    confidence_drop = round(rows[0]["confidence"] - rows[-1]["confidence"], 6)
    strict_decreases = sum(
        1
        for lower, higher in zip(rows, rows[1:])
        if higher["confidence"] < lower["confidence"] - 1e-9
    )
    return {
        "profiles": rows,
        "balancedToConcentratedDrop": confidence_drop,
        "strictDecreaseSteps": strict_decreases,
        "requiredDrop": MIN_CONCENTRATION_DROP,
        "passed": (
            confidence_drop >= MIN_CONCENTRATION_DROP
            and strict_decreases == len(rows) - 1
        ),
    }


def volume_saturation_analysis_v2() -> dict[str, object]:
    topology = {"apps": 1, "regions": 1, "clusters": 1, "gateways": 1, "paths": 1}
    rows = [
        evaluate_profile_v2(events=events, **topology)
        for events in (10, 25, 50, 100, 500, 2_000, 10_000)
    ]
    gain = round(rows[-1]["confidence"] - rows[3]["confidence"], 6)
    return {
        "profiles": rows,
        "gainFrom100To10000": gain,
        "maxAllowedGain": MAX_POST_SATURATION_GAIN,
        "passed": gain <= MAX_POST_SATURATION_GAIN,
    }


def adversarial_ranking_analysis_v2() -> dict[str, object]:
    independent = evaluate_profile_v2(
        events=50,
        apps=10,
        regions=3,
        clusters=4,
        gateways=4,
        paths=4,
        gateway_concentration=0.25,
        path_concentration=0.25,
    )
    high_volume_concentrated = evaluate_profile_v2(
        events=5_000,
        apps=50,
        regions=3,
        clusters=4,
        gateways=4,
        paths=4,
        gateway_concentration=0.99,
        path_concentration=0.99,
    )
    delta = round(high_volume_concentrated["confidence"] - independent["confidence"], 6)
    return {
        "independent": independent,
        "highVolumeConcentrated": high_volume_concentrated,
        "confidenceDelta": delta,
        "passed": high_volume_concentrated["confidence"] <= independent["confidence"],
    }


def _phase_b_summary(
    matrix: list[dict[str, object]],
    partial_correlation: dict[str, object],
    volume_saturation: dict[str, object],
    adversarial_ranking: dict[str, object],
) -> dict[str, object]:
    monotonicity = monotonicity_analysis(matrix)
    checks = {
        "topologyMonotonicity": monotonicity["violationCount"] == 0,
        "postSaturationVolumeBounded": volume_saturation["passed"],
        "partialCorrelationSensitivity": partial_correlation["passed"],
        "adversarialRanking": adversarial_ranking["passed"],
    }
    return {
        "profilesEvaluated": len(matrix),
        "monotonicity": monotonicity,
        "partialCorrelation": partial_correlation,
        "volumeSaturation": volume_saturation,
        "adversarialRanking": adversarial_ranking,
        "claimChecks": checks,
        "claimPasses": sum(checks.values()),
        "claimCount": len(checks),
        "allPassed": all(checks.values()),
    }


def build_report() -> dict[str, object]:
    commit, dirty = repository_provenance()

    phase_a_v1 = evaluate_phase_a_v1()
    phase_a_v2 = evaluate_phase_a_v2()

    matrix_v1 = matrix_profiles()
    phase_b_v1 = _phase_b_summary(
        matrix_v1,
        concentration_analysis(),
        volume_saturation_analysis(),
        adversarial_ranking_analysis(),
    )

    matrix_v2 = matrix_profiles_v2()
    phase_b_v2 = _phase_b_summary(
        matrix_v2,
        concentration_analysis_v2(),
        volume_saturation_analysis_v2(),
        adversarial_ranking_analysis_v2(),
    )

    checks = {
        "v1BaselinePreserved": phase_a_v1["allPassed"] and not phase_b_v1["allPassed"],
        "v2PreservesPhaseA": phase_a_v2["allPassed"],
        "v2PassesFrozenPhaseB": phase_b_v2["allPassed"],
        "frozenSweepSizePreserved": (
            phase_b_v1["profilesEvaluated"]
            == phase_b_v2["profilesEvaluated"]
            == 1782
        ),
    }

    return {
        "lab": "SHIELD Lab #001",
        "phase": "v2 — evidence-driven scoring revision validation",
        "runnerVersion": RUNNER_VERSION,
        "sweepVersion": SWEEP_VERSION,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "frozenSweepDigest": stable_digest(SWEEP_CONFIG),
        "v1": {
            "scoringVersion": SCORING_VERSION,
            "scoringDigest": scoring_digest(),
            "phaseA": phase_a_v1,
            "phaseB": phase_b_v1,
        },
        "v2": {
            "scoringVersion": SCORING_VERSION_V2,
            "scoringDigest": scoring_digest_v2(),
            "scoringConfig": SHIELD_CONFIG_V2,
            "phaseA": phase_a_v2,
            "phaseB": phase_b_v2,
        },
        "validationChecks": checks,
        "summary": {
            "checkPasses": sum(checks.values()),
            "checkCount": len(checks),
            "allPassed": all(checks.values()),
        },
        "interpretation": (
            "V2 is accepted by this validation only if the original v1 outcome is "
            "reproduced, all fixed Phase A scenarios still pass, and the unchanged "
            "1,782-profile Phase B stress suite passes without weakening its criteria."
        ),
        "limitations": [
            "V2 was designed in direct response to the Phase B concentration counterexample, so passing that frozen suite is evidence of regression repair, not independent real-world validation.",
            "Inverse-Simpson effective counts measure distribution concentration but do not prove causal independence.",
            "The experiment remains synthetic and does not measure incident precision, recall, temporal decay, or remediation safety.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    v1 = report["v1"]
    v2 = report["v2"]
    v1_b = v1["phaseB"]
    v2_b = v2["phaseB"]
    summary = report["summary"]

    lines = [
        "# SHIELD Lab #001 — V2 Validation Summary",
        "",
        f"**Overall:** {'PASS' if summary['allPassed'] else 'FAIL'}  ",
        f"**Repository:** `{report['repositoryCommit']}` (dirty={report['repositoryDirty']})  ",
        f"**Frozen sweep:** `{report['frozenSweepDigest']}`  ",
        f"**V1:** `{v1['scoringVersion']}`  ",
        f"**V2:** `{v2['scoringVersion']}`",
        "",
        "## Before and after",
        "",
        "| Validation | V1 | V2 |",
        "|---|---:|---:|",
        f"| Phase A fixed scenarios | {'PASS' if v1['phaseA']['allPassed'] else 'FAIL'} ({v1['phaseA']['scenarioPasses']}/{v1['phaseA']['scenarioCount']}) | {'PASS' if v2['phaseA']['allPassed'] else 'FAIL'} ({v2['phaseA']['scenarioPasses']}/{v2['phaseA']['scenarioCount']}) |",
        f"| Phase B frozen checks | {'PASS' if v1_b['allPassed'] else 'FAIL'} ({v1_b['claimPasses']}/{v1_b['claimCount']}) | {'PASS' if v2_b['allPassed'] else 'FAIL'} ({v2_b['claimPasses']}/{v2_b['claimCount']}) |",
        f"| Phase B profiles | {v1_b['profilesEvaluated']:,} | {v2_b['profilesEvaluated']:,} |",
        f"| Concentration drop | {v1_b['partialCorrelation']['balancedToConcentratedDrop']:.6f} | {v2_b['partialCorrelation']['balancedToConcentratedDrop']:.6f} |",
        f"| Adversarial ranking delta | {v1_b['adversarialRanking']['confidenceDelta']:.6f} | {v2_b['adversarialRanking']['confidenceDelta']:.6f} |",
        "",
        "## V2 partial-correlation sweep",
        "",
        "| Requested concentration | Effective gateways | Effective paths | Confidence |",
        "|---:|---:|---:|---:|",
    ]
    for row in v2_b["partialCorrelation"]["profiles"]:
        lines.append(
            f"| {row['requestedConcentration']:.2f} | "
            f"{row['effectiveCounts']['gateways']:.3f} | "
            f"{row['effectiveCounts']['paths']:.3f} | "
            f"{row['confidence']:.6f} |"
        )

    lines.extend(["", "## Validation checks", ""])
    for name, passed in report["validationChecks"].items():
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
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate SHIELD evidence score v2 against frozen Phase A and Phase B."
    )
    parser.add_argument(
        "--output",
        default="labs/shield_001/results/v2-validation-latest.json",
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
