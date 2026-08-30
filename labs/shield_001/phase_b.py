from __future__ import annotations

import argparse
import itertools
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .core import Observation, SCORING_VERSION, SHIELD_CONFIG, shield_detector, stable_digest

RUNNER_VERSION = "shield-phase-b-runner-v1"
SWEEP_VERSION = "shield-phase-b-sweep-v1"

EVENT_LEVELS = (10, 25, 50, 100, 500, 2_000)
APP_LEVELS = (1, 5, 10, 50)
REGION_LEVELS = (1, 2, 3)
CLUSTER_LEVELS = (1, 2, 4)
GATEWAY_LEVELS = (1, 2, 4)
PATH_LEVELS = (1, 2, 4)
CONCENTRATION_LEVELS = (0.25, 0.50, 0.75, 0.90, 0.99)

MIN_CONCENTRATION_DROP = 0.10
MAX_POST_SATURATION_GAIN = 0.01

SWEEP_CONFIG = {
    "eventLevels": EVENT_LEVELS,
    "appLevels": APP_LEVELS,
    "regionLevels": REGION_LEVELS,
    "clusterLevels": CLUSTER_LEVELS,
    "gatewayLevels": GATEWAY_LEVELS,
    "pathLevels": PATH_LEVELS,
    "concentrationLevels": CONCENTRATION_LEVELS,
    "minConcentrationDrop": MIN_CONCENTRATION_DROP,
    "maxPostSaturationGain": MAX_POST_SATURATION_GAIN,
}


def _balanced_values(prefix: str, count: int, total: int) -> list[str]:
    return [f"{prefix}-{index % count + 1}" for index in range(total)]


def _concentrated_values(prefix: str, count: int, total: int, ratio: float) -> list[str]:
    if count <= 1:
        return [f"{prefix}-1"] * total
    if total < count:
        raise ValueError("total must be >= count so every topology value is represented")

    dominant = max(1, min(total - (count - 1), round(total * ratio)))
    values = [f"{prefix}-1"] * dominant
    remaining = total - dominant
    values.extend(f"{prefix}-{index % (count - 1) + 2}" for index in range(remaining))
    return values


def build_observations(
    *,
    events: int,
    apps: int,
    regions: int,
    clusters: int,
    gateways: int,
    paths: int,
    gateway_concentration: float | None = None,
    path_concentration: float | None = None,
) -> tuple[Observation, ...]:
    if events < max(apps, regions, clusters, gateways, paths):
        raise ValueError("events must cover all requested unique topology values")

    sequences = {
        "app": _balanced_values("app", apps, events),
        "instance": _balanced_values("instance", max(apps, 1), events),
        "host": _balanced_values("host", max(apps, 1), events),
        "cluster": _balanced_values("cluster", clusters, events),
        "region": _balanced_values("region", regions, events),
        "gateway": (
            _concentrated_values("gateway", gateways, events, gateway_concentration)
            if gateway_concentration is not None
            else _balanced_values("gateway", gateways, events)
        ),
        "path": (
            _concentrated_values("path", paths, events, path_concentration)
            if path_concentration is not None
            else _balanced_values("path", paths, events)
        ),
        "session": _balanced_values("session", min(events, max(apps * 2, 1)), events),
    }

    return tuple(
        Observation(
            app=sequences["app"][index],
            instance=sequences["instance"][index],
            host=sequences["host"][index],
            cluster=sequences["cluster"][index],
            region=sequences["region"][index],
            gateway=sequences["gateway"][index],
            path=sequences["path"][index],
            session=sequences["session"][index],
        )
        for index in range(events)
    )


def evaluate_profile(**profile: object) -> dict[str, object]:
    observations = build_observations(**profile)
    shield = shield_detector(observations)
    return {
        "profile": profile,
        "confidence": shield["confidence"],
        "tier": shield["tier"],
        "independenceFactor": shield["independenceFactor"],
        "concentration": shield["concentration"],
    }


def matrix_profiles() -> list[dict[str, object]]:
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
            evaluate_profile(
                events=events,
                apps=apps,
                regions=regions,
                clusters=clusters,
                gateways=gateways,
                paths=paths,
            )
        )
    return rows


def _profile_key(row: dict[str, object], omit: str) -> tuple[tuple[str, object], ...]:
    profile = row["profile"]
    return tuple(
        (key, profile[key])
        for key in ("events", "apps", "regions", "clusters", "gateways", "paths")
        if key != omit
    )


def _group_rows(rows: list[dict[str, object]], dimension: str) -> dict[object, list[dict[str, object]]]:
    groups: dict[object, list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(_profile_key(row, dimension), []).append(row)
    return groups


def monotonicity_analysis(rows: list[dict[str, object]]) -> dict[str, object]:
    violations: list[dict[str, object]] = []
    comparisons = 0

    for dimension in ("apps", "regions", "clusters", "gateways", "paths"):
        for group in _group_rows(rows, dimension).values():
            ordered = sorted(group, key=lambda row: row["profile"][dimension])
            comparisons += max(len(ordered) - 1, 0)
            for lower, higher in zip(ordered, ordered[1:]):
                if higher["confidence"] + 1e-9 < lower["confidence"]:
                    violations.append(
                        {
                            "dimension": dimension,
                            "lower": lower,
                            "higher": higher,
                            "delta": round(higher["confidence"] - lower["confidence"], 6),
                        }
                    )

    violations.sort(key=lambda item: item["delta"])
    return {
        "comparisons": comparisons,
        "violationCount": len(violations),
        "worstViolations": violations[:10],
    }


def concentration_analysis() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for ratio in CONCENTRATION_LEVELS:
        row = evaluate_profile(
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


def volume_saturation_analysis() -> dict[str, object]:
    topology = {"apps": 1, "regions": 1, "clusters": 1, "gateways": 1, "paths": 1}
    rows = [
        evaluate_profile(events=events, **topology)
        for events in (10, 25, 50, 100, 500, 2_000, 10_000)
    ]
    gain = round(rows[-1]["confidence"] - rows[3]["confidence"], 6)
    return {
        "profiles": rows,
        "gainFrom100To10000": gain,
        "maxAllowedGain": MAX_POST_SATURATION_GAIN,
        "passed": gain <= MAX_POST_SATURATION_GAIN,
    }


def adversarial_ranking_analysis() -> dict[str, object]:
    independent = evaluate_profile(
        events=50,
        apps=10,
        regions=3,
        clusters=4,
        gateways=4,
        paths=4,
        gateway_concentration=0.25,
        path_concentration=0.25,
    )
    high_volume_concentrated = evaluate_profile(
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


def cliff_analysis(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    changes: list[dict[str, object]] = []
    for dimension in ("events", "apps", "regions", "clusters", "gateways", "paths"):
        for group in _group_rows(rows, dimension).values():
            ordered = sorted(group, key=lambda row: row["profile"][dimension])
            for lower, higher in zip(ordered, ordered[1:]):
                changes.append(
                    {
                        "dimension": dimension,
                        "from": lower["profile"][dimension],
                        "to": higher["profile"][dimension],
                        "delta": round(higher["confidence"] - lower["confidence"], 6),
                        "base": {
                            key: value
                            for key, value in lower["profile"].items()
                            if key != dimension
                        },
                    }
                )
    changes.sort(key=lambda item: abs(item["delta"]), reverse=True)
    return changes[:10]


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
    matrix = matrix_profiles()
    monotonicity = monotonicity_analysis(matrix)
    partial_correlation = concentration_analysis()
    volume_saturation = volume_saturation_analysis()
    adversarial_ranking = adversarial_ranking_analysis()
    commit, dirty = repository_provenance()

    checks = {
        "topologyMonotonicity": monotonicity["violationCount"] == 0,
        "postSaturationVolumeBounded": volume_saturation["passed"],
        "partialCorrelationSensitivity": partial_correlation["passed"],
        "adversarialRanking": adversarial_ranking["passed"],
    }
    confidences = [row["confidence"] for row in matrix]

    return {
        "lab": "SHIELD Lab #001",
        "phase": "B — adversarial sensitivity and partial correlation",
        "runnerVersion": RUNNER_VERSION,
        "sweepVersion": SWEEP_VERSION,
        "scoringVersion": SCORING_VERSION,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "sweepDigest": stable_digest(SWEEP_CONFIG),
        "scoringConfigDigest": stable_digest(SHIELD_CONFIG),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "sweepConfig": SWEEP_CONFIG,
        "matrix": {
            "profilesEvaluated": len(matrix),
            "minConfidence": min(confidences),
            "maxConfidence": max(confidences),
            "lowTier": sum(row["tier"] == "low" for row in matrix),
            "mediumTier": sum(row["tier"] == "medium" for row in matrix),
            "highTier": sum(row["tier"] == "high" for row in matrix),
        },
        "analyses": {
            "monotonicity": monotonicity,
            "partialCorrelation": partial_correlation,
            "volumeSaturation": volume_saturation,
            "adversarialRanking": adversarial_ranking,
            "largestAdjacentChanges": cliff_analysis(matrix),
        },
        "claimChecks": checks,
        "summary": {
            "claimPasses": sum(checks.values()),
            "claimCount": len(checks),
            "allPassed": all(checks.values()),
        },
        "interpretation": (
            "Phase B challenges shield-evidence-score-v1. A FAIL is a valid experimental result "
            "and identifies where the candidate score must be revised; it is not a failure of "
            "the SHIELD architectural principle itself."
        ),
        "limitations": [
            "Synthetic deterministic topologies are proxies for causal independence.",
            "The concentration sweep preserves topology cardinality while changing traffic concentration; real causal correlation may require richer graph metadata.",
            "Phase B tests score behavior, not incident ground truth, precision/recall, temporal decay, or remediation authority.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    analyses = report["analyses"]
    summary = report["summary"]
    lines = [
        "# SHIELD Lab #001 — Phase B Summary",
        "",
        f"**Overall:** {'PASS' if summary['allPassed'] else 'FAIL'}  ",
        f"**Scoring:** `{report['scoringVersion']}`  ",
        f"**Repository:** `{report['repositoryCommit']}` (dirty={report['repositoryDirty']})  ",
        f"**Sweep digest:** `{report['sweepDigest']}`  ",
        f"**Scoring digest:** `{report['scoringConfigDigest']}`",
        "",
        "## Matrix",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Profiles evaluated | {report['matrix']['profilesEvaluated']:,} |",
        f"| Monotonicity violations | {analyses['monotonicity']['violationCount']} |",
        f"| Concentration confidence drop | {analyses['partialCorrelation']['balancedToConcentratedDrop']:.6f} |",
        f"| 100→10,000 correlated-event gain | {analyses['volumeSaturation']['gainFrom100To10000']:.6f} |",
        f"| Adversarial ranking delta | {analyses['adversarialRanking']['confidenceDelta']:.6f} |",
        "",
        "## Claim checks",
        "",
    ]
    for name, passed in report["claimChecks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")

    lines.extend(
        [
            "",
            "## Partial-correlation sweep",
            "",
            "| Requested concentration | Observed gateway concentration | Observed path concentration | Confidence |",
            "|---:|---:|---:|---:|",
        ]
    )
    for row in analyses["partialCorrelation"]["profiles"]:
        lines.append(
            f"| {row['requestedConcentration']:.2f} | "
            f"{row['concentration']['gateways']:.3f} | "
            f"{row['concentration']['paths']:.3f} | "
            f"{row['confidence']:.6f} |"
        )

    lines.extend(["", "## Interpretation", "", report["interpretation"], "", "## Limitations", ""])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SHIELD Lab #001 Phase B adversarial sweep.")
    parser.add_argument(
        "--output",
        default="labs/shield_001/results/phase-b-latest.json",
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

    # A non-zero exit is intentional when the candidate score violates a predeclared Phase B check.
    raise SystemExit(0 if report["summary"]["allPassed"] else 2)


if __name__ == "__main__":
    main()
