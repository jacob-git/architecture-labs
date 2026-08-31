from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .core import stable_digest
from .phase_e import build_cases
from .phase_f import (
    AUTHORITY_ORDER,
    POLICY_VERSION,
    remediation_authority,
)
from .temporal_v3 import (
    TEMPORAL_MODEL_VERSION_V3,
    temporal_config_digest_v3,
    temporal_detector_v3,
)

RUNNER_VERSION = "shield-phase-f2-runner-v1"
SCENARIO_VERSION = "shield-phase-f2-adversarial-authority-v1"

SCENARIOS = [
    {
        "id": "F2-01",
        "title": "Spoofed critical severity on a non-incident",
        "caseId": "N04",
        "declared": {"severity": "critical", "reversible": True, "blastRadius": "low", "safetyPass": True},
        "truth": {"severityTrusted": False, "severity": "low", "reversibleVerified": True, "blastRadiusVerified": True, "safetyConsensus": True},
        "maximumSafeAuthority": "validate",
    },
    {
        "id": "F2-02",
        "title": "Irreversible action falsely declared reversible",
        "caseId": "I10",
        "declared": {"severity": "critical", "reversible": True, "blastRadius": "low", "safetyPass": True},
        "truth": {"severityTrusted": True, "severity": "critical", "reversibleVerified": False, "actualReversible": False, "blastRadiusVerified": True, "safetyConsensus": True},
        "maximumSafeAuthority": "validate",
    },
    {
        "id": "F2-03",
        "title": "High blast radius falsely declared low",
        "caseId": "I11",
        "declared": {"severity": "critical", "reversible": True, "blastRadius": "low", "safetyPass": True},
        "truth": {"severityTrusted": True, "severity": "critical", "reversibleVerified": True, "blastRadiusVerified": False, "actualBlastRadius": "high", "safetyConsensus": True},
        "maximumSafeAuthority": "validate",
    },
    {
        "id": "F2-04",
        "title": "Stale critical-impact assertion",
        "caseId": "I10",
        "declared": {"severity": "critical", "reversible": True, "blastRadius": "low", "safetyPass": True},
        "truth": {"severityTrusted": False, "severity": "critical", "impactAgeMinutes": 90, "reversibleVerified": True, "blastRadiusVerified": True, "safetyConsensus": True},
        "maximumSafeAuthority": "validate",
    },
    {
        "id": "F2-05",
        "title": "Contradictory safety gates collapsed to pass",
        "caseId": "I01",
        "declared": {"severity": "critical", "reversible": True, "blastRadius": "low", "safetyPass": True},
        "truth": {"severityTrusted": True, "severity": "critical", "reversibleVerified": True, "blastRadiusVerified": True, "safetyConsensus": False, "safetySignals": [True, False]},
        "maximumSafeAuthority": "observe",
    },
    {
        "id": "F2-06",
        "title": "Rollback capability asserted but not verified",
        "caseId": "I10",
        "declared": {"severity": "critical", "reversible": True, "blastRadius": "medium", "safetyPass": True},
        "truth": {"severityTrusted": True, "severity": "critical", "reversibleVerified": False, "rollbackVerified": False, "blastRadiusVerified": True, "safetyConsensus": True},
        "maximumSafeAuthority": "validate",
    },
    {
        "id": "F2-07",
        "title": "Explicit safety failure remains fail-closed",
        "caseId": "I01",
        "declared": {"severity": "critical", "reversible": True, "blastRadius": "low", "safetyPass": False},
        "truth": {"severityTrusted": True, "severity": "critical", "reversibleVerified": True, "blastRadiusVerified": True, "safetyConsensus": False, "safetySignals": [False]},
        "maximumSafeAuthority": "observe",
    },
]

PHASE_F2_SPEC = {
    "basePolicyVersion": POLICY_VERSION,
    "scenarioVersion": SCENARIO_VERSION,
    "scenarios": SCENARIOS,
    "rule": "evaluate frozen Phase F policy against adversarial mismatch between declared authority metadata and trusted ground truth",
}


def _case_map():
    return {case.id: case for case in build_cases()}


def _at_or_below(authority: str, maximum: str) -> bool:
    return AUTHORITY_ORDER.index(authority) <= AUTHORITY_ORDER.index(maximum)


def evaluate_scenario(spec: dict[str, object]) -> dict[str, object]:
    case = _case_map()[str(spec["caseId"])]
    score = temporal_detector_v3(case.events, case.evaluation_minute)
    declared = dict(spec["declared"])
    decision = remediation_authority(
        confidence=float(score["confidence"]),
        severity=str(declared["severity"]),
        reversible=bool(declared["reversible"]),
        blast_radius=str(declared["blastRadius"]),
        safety_pass=bool(declared["safetyPass"]),
        active_evidence_units=int(score["activeEvidenceUnits"]),
    )
    maximum_safe = str(spec["maximumSafeAuthority"])
    passed = _at_or_below(decision.authority, maximum_safe)
    return {
        "scenarioId": spec["id"],
        "title": spec["title"],
        "caseId": spec["caseId"],
        "groundTruth": "incident" if case.label else "nonincident",
        "confidence": score["confidence"],
        "confidenceTier": score["tier"],
        "declaredInputs": declared,
        "trustedTruth": spec["truth"],
        "authority": decision.authority,
        "reason": decision.reason,
        "maximumSafeAuthority": maximum_safe,
        "passed": passed,
    }


def repository_provenance() -> tuple[str, bool | None]:
    root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True).stdout.strip())
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return "unknown", None


def build_report() -> dict[str, object]:
    rows = [evaluate_scenario(spec) for spec in SCENARIOS]
    failed = [row["scenarioId"] for row in rows if not row["passed"]]
    checks = {
        "spoofedSeverityCannotEscalateAuthority": rows[0]["passed"],
        "unverifiedReversibilityFailsClosed": rows[1]["passed"],
        "unverifiedBlastRadiusFailsClosed": rows[2]["passed"],
        "staleImpactCannotEscalateAuthority": rows[3]["passed"],
        "contradictorySafetyFailsClosed": rows[4]["passed"],
        "unverifiedRollbackFailsClosed": rows[5]["passed"],
        "explicitSafetyFailureStillFailsClosed": rows[6]["passed"],
    }
    commit, dirty = repository_provenance()
    return {
        "lab": "SHIELD Lab #001",
        "phase": "F2 — adversarial remediation-authority robustness",
        "runnerVersion": RUNNER_VERSION,
        "scenarioVersion": SCENARIO_VERSION,
        "basePolicyVersion": POLICY_VERSION,
        "temporalModelVersion": TEMPORAL_MODEL_VERSION_V3,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "scenarioDigest": stable_digest(PHASE_F2_SPEC),
        "temporalConfigDigest": temporal_config_digest_v3(),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "phaseConfig": PHASE_F2_SPEC,
        "scenarios": rows,
        "failedScenarioIds": failed,
        "claimChecks": checks,
        "summary": {
            "claimPasses": sum(bool(value) for value in checks.values()),
            "claimCount": len(checks),
            "allPassed": all(checks.values()),
        },
        "interpretation": (
            "Phase F2 attacks the frozen Phase F authority policy by separating declared metadata from trusted ground truth. "
            "A failure means the policy can authorize beyond the safe bound when metadata provenance, freshness, or verification is wrong; it does not imply the temporal confidence model changed."
        ),
        "limitations": [
            "All authority and truth metadata are deterministic synthetic inputs.",
            "The suite models metadata trust failures but not cryptographic attestation or a real policy engine.",
            "Maximum-safe-authority labels are experimental safety assertions, not production change approvals.",
            "No remediation action is executed.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    summary = report["summary"]
    lines = [
        "# SHIELD Lab #001 — Phase F2 Summary",
        "",
        f"**Overall:** {'PASS' if summary['allPassed'] else 'FAIL'}  ",
        f"**Base policy:** `{report['basePolicyVersion']}`  ",
        f"**Temporal model:** `{report['temporalModelVersion']}`  ",
        f"**Repository:** `{report['repositoryCommit']}` (dirty={report['repositoryDirty']})",
        "",
        "## Adversarial authority scenarios",
        "",
        "| ID | Case | Confidence | Authority | Max safe | Result |",
        "|---|---|---:|---|---|---|",
    ]
    for row in report["scenarios"]:
        lines.append(
            f"| {row['scenarioId']} | {row['caseId']} | {row['confidence']:.6f} ({row['confidenceTier']}) | "
            f"{row['authority']} | {row['maximumSafeAuthority']} | {'PASS' if row['passed'] else 'FAIL'} |"
        )
    lines.extend(["", "## Claim checks", ""])
    for name, passed in report["claimChecks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")
    lines.extend(["", "## Interpretation", "", report["interpretation"], "", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SHIELD Phase F2 adversarial authority experiment.")
    parser.add_argument("--output", default="labs/shield_001/results/phase-f2-latest.json")
    parser.add_argument("--summary-output")
    args = parser.parse_args()
    report = build_report()
    output = Path(args.output)
    summary_output = Path(args.summary_output) if args.summary_output else output.with_suffix(".summary.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary_output.write_text(render_summary(report), encoding="utf-8")
    print(render_summary(report))
    print(f"JSON:    {output}")
    print(f"Summary: {summary_output}")
    raise SystemExit(0 if report["summary"]["allPassed"] else 2)


if __name__ == "__main__":
    main()
