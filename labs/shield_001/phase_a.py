from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .core import (
    RUNNER_VERSION,
    SCENARIO_VERSION,
    SCORING_VERSION,
    SHIELD_CONFIG,
    build_scenarios,
    evaluate_scenario,
    scenario_digest,
    scoring_digest,
)


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
    started_at = datetime.now(timezone.utc).isoformat()
    commit, dirty = repository_provenance()
    results = [evaluate_scenario(scenario) for scenario in build_scenarios()]

    pairwise_claim = {
        "independentBeatsCorrelated": (
            results[1]["shield"]["confidence"] > results[0]["shield"]["confidence"]
        ),
        "hiddenCorrelationDiscounted": (
            results[2]["shield"]["confidence"] < results[1]["shield"]["confidence"]
        ),
        "moreEventsDoNotGuaranteeMoreConfidence": (
            results[2]["counts"]["events"] > results[1]["counts"]["events"]
            and results[2]["shield"]["confidence"] < results[1]["shield"]["confidence"]
        ),
    }

    return {
        "lab": "SHIELD Lab #001",
        "phase": "A — deterministic independent-evidence validation",
        "runnerVersion": RUNNER_VERSION,
        "scenarioVersion": SCENARIO_VERSION,
        "scoringVersion": SCORING_VERSION,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "scenarioDigest": scenario_digest(),
        "scoringDigest": scoring_digest(),
        "startedAt": started_at,
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "config": SHIELD_CONFIG,
        "results": results,
        "claimChecks": pairwise_claim,
        "summary": {
            "scenarios": len(results),
            "scenarioPasses": sum(1 for r in results if r["passed"]),
            "claimPasses": sum(1 for passed in pairwise_claim.values() if passed),
            "allPassed": all(r["passed"] for r in results) and all(pairwise_claim.values()),
        },
        "limitations": [
            "The observations and topology are synthetic and deterministic.",
            "The SHIELD score is a candidate experimental function, not a canonical or validated universal formula.",
            "This phase tests evidence weighting behavior, not real incident diagnosis, causal discovery, or remediation safety.",
            "Thresholds and diversity targets are fixed lab parameters and require sensitivity testing in later phases.",
        ],
    }


def render_summary_markdown(report: dict[str, object]) -> str:
    summary = report["summary"]
    rows = []
    for result in report["results"]:
        raw = "ESCALATE" if result["rawThreshold"]["escalated"] else "hold"
        distinct = "ESCALATE" if result["distinctReporter"]["escalated"] else "hold"
        shield = result["shield"]
        rows.append(
            "| "
            f"`{result['scenarioId']}` | "
            f"{result['counts']['events']:,} | "
            f"{result['counts']['apps']} | "
            f"{result['counts']['gateways']} | "
            f"{result['counts']['paths']} | "
            f"{raw} | {distinct} | "
            f"{shield['confidence']:.3f} ({shield['tier']}) | "
            f"{'PASS' if result['passed'] else 'FAIL'} |"
        )

    claims = "\n".join(
        f"- {'PASS' if passed else 'FAIL'} `{name}`"
        for name, passed in report["claimChecks"].items()
    )
    limitations = "\n".join(f"- {item}" for item in report["limitations"])

    return (
        "# SHIELD Lab #001 — Phase A Run Summary\n\n"
        f"**Overall:** {'PASS' if summary['allPassed'] else 'FAIL'}  \n"
        f"**Run timestamp (UTC):** `{report['startedAt']}`  \n"
        f"**Repository commit:** `{report['repositoryCommit']}`  \n"
        f"**Repository dirty:** `{report['repositoryDirty']}`  \n"
        f"**Python:** `{report['pythonVersion']}`  \n"
        f"**Platform:** `{report['platform']}`  \n"
        f"**Runner:** `{report['runnerVersion']}`  \n"
        f"**Scenario version:** `{report['scenarioVersion']}`  \n"
        f"**Scoring version:** `{report['scoringVersion']}`  \n"
        f"**Scenario digest:** `{report['scenarioDigest']}`  \n"
        f"**Scoring digest:** `{report['scoringDigest']}`\n\n"
        "## Scenario results\n\n"
        "| Scenario | Events | Apps | Gateways | Paths | Raw | Distinct | SHIELD | Result |\n"
        "|---|---:|---:|---:|---:|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n"
        "## Claim checks\n\n"
        f"{claims}\n\n"
        "## Totals\n\n"
        f"- Scenario checks: **{summary['scenarioPasses']}/{summary['scenarios']}**\n"
        f"- Claim checks: **{summary['claimPasses']}/{len(report['claimChecks'])}**\n"
        f"- Overall: **{'PASS' if summary['allPassed'] else 'FAIL'}**\n\n"
        "## Interpretation boundary\n\n"
        "This run shows that the committed candidate scoring function behaves as specified "
        "on the committed synthetic scenarios. It does not establish production incident "
        "detection accuracy or validate SHIELD as a universal architecture.\n\n"
        "## Limitations\n\n"
        f"{limitations}\n"
    )


def print_summary(report: dict[str, object]) -> None:
    print("SHIELD Lab #001 — Phase A")
    print("=" * 44)
    for result in report["results"]:
        raw = "ESCALATE" if result["rawThreshold"]["escalated"] else "hold"
        distinct = "ESCALATE" if result["distinctReporter"]["escalated"] else "hold"
        shield = result["shield"]
        status = "PASS" if result["passed"] else "FAIL"
        print(f"{result['scenarioId']}: {status}")
        print(
            f"  events={result['counts']['events']:,} apps={result['counts']['apps']} "
            f"gateways={result['counts']['gateways']} paths={result['counts']['paths']}"
        )
        print(f"  raw={raw} distinct={distinct} SHIELD={shield['confidence']:.3f} ({shield['tier']})")
    print("-" * 44)
    summary = report["summary"]
    print(f"Scenario checks: {summary['scenarioPasses']}/{summary['scenarios']}")
    print(f"Claim checks:    {summary['claimPasses']}/{len(report['claimChecks'])}")
    print(f"Overall:         {'PASS' if summary['allPassed'] else 'FAIL'}")
    print(f"Repository:      {report['repositoryCommit']} dirty={report['repositoryDirty']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SHIELD Lab #001 Phase A.")
    parser.add_argument(
        "--output",
        default="labs/shield_001/results/phase-a-latest.json",
        help="JSON result path (default: labs/shield_001/results/phase-a-latest.json)",
    )
    parser.add_argument(
        "--summary-output",
        default=None,
        help="Markdown summary path (default: same path as --output with .summary.md suffix)",
    )
    parser.add_argument("--stdout-json", action="store_true", help="Also print the complete JSON report.")
    args = parser.parse_args()

    report = build_report()

    output = Path(args.output)
    summary_output = Path(args.summary_output) if args.summary_output else output.with_suffix(".summary.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)

    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary_output.write_text(render_summary_markdown(report), encoding="utf-8")

    print_summary(report)
    print(f"JSON result:      {output}")
    print(f"Summary:          {summary_output}")
    if args.stdout_json:
        json.dump(report, sys.stdout, indent=2)
        print()

    raise SystemExit(0 if report["summary"]["allPassed"] else 1)


if __name__ == "__main__":
    main()
