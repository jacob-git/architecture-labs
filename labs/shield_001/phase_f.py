from __future__ import annotations

import argparse
import json
import platform
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .core import stable_digest
from .phase_e import build_cases
from .temporal_v3 import (
    TEMPORAL_MODEL_VERSION_V3,
    temporal_config_digest_v3,
    temporal_detector_v3,
)

RUNNER_VERSION = "shield-phase-f-runner-v1"
POLICY_VERSION = "shield-remediation-authority-policy-v1"
SCENARIO_VERSION = "shield-phase-f-authority-scenarios-v1"

AUTHORITY_ORDER = ["observe", "enrich", "validate", "mitigate", "isolate", "recover"]
SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
BLAST_RADIUS_ORDER = {"low": 0, "medium": 1, "high": 2}

POLICY = {
    "confidence_tiers": {"low_below": 0.35, "medium_below": 0.75, "high_at_or_above": 0.75},
    "principles": [
        "confidence and severity are independent inputs",
        "severity can increase urgency but cannot manufacture evidentiary confidence",
        "irreversible or broad actions require high confidence and explicit safety",
        "medium-confidence critical incidents may receive only bounded reversible mitigation",
        "failed safety gates cap authority at observe",
    ],
}

SCENARIOS = [
    {"id": "F01", "caseId": "I01", "severity": "critical", "reversible": True, "blastRadius": "low", "safetyPass": True, "expectedAuthority": "isolate"},
    {"id": "F02", "caseId": "I04", "severity": "high", "reversible": True, "blastRadius": "low", "safetyPass": True, "expectedAuthority": "mitigate"},
    {"id": "F03", "caseId": "I10", "severity": "critical", "reversible": True, "blastRadius": "low", "safetyPass": True, "expectedAuthority": "mitigate"},
    {"id": "F04", "caseId": "I11", "severity": "critical", "reversible": True, "blastRadius": "medium", "safetyPass": True, "expectedAuthority": "mitigate"},
    {"id": "F05", "caseId": "I12", "severity": "critical", "reversible": False, "blastRadius": "high", "safetyPass": True, "expectedAuthority": "validate"},
    {"id": "F06", "caseId": "N01", "severity": "low", "reversible": True, "blastRadius": "low", "safetyPass": True, "expectedAuthority": "enrich"},
    {"id": "F07", "caseId": "N07", "severity": "medium", "reversible": True, "blastRadius": "low", "safetyPass": True, "expectedAuthority": "observe"},
    {"id": "F08", "caseId": "I01", "severity": "critical", "reversible": True, "blastRadius": "low", "safetyPass": False, "expectedAuthority": "observe"},
    {"id": "F09", "caseId": "I01", "severity": "critical", "reversible": False, "blastRadius": "high", "safetyPass": True, "expectedAuthority": "validate"},
    {"id": "F10", "caseId": "N04", "severity": "high", "reversible": True, "blastRadius": "low", "safetyPass": True, "expectedAuthority": "validate"},
]

PHASE_F_SPEC = {
    "policyVersion": POLICY_VERSION,
    "scenarioVersion": SCENARIO_VERSION,
    "policy": POLICY,
    "scenarios": SCENARIOS,
}


@dataclass(frozen=True)
class AuthorityDecision:
    authority: str
    reason: str


def _confidence_tier(confidence: float) -> str:
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.35:
        return "medium"
    return "low"


def _cap(authority: str, maximum: str) -> str:
    return AUTHORITY_ORDER[min(AUTHORITY_ORDER.index(authority), AUTHORITY_ORDER.index(maximum))]


def remediation_authority(
    *,
    confidence: float,
    severity: str,
    reversible: bool,
    blast_radius: str,
    safety_pass: bool,
    active_evidence_units: int,
) -> AuthorityDecision:
    if severity not in SEVERITY_ORDER:
        raise ValueError(f"unknown severity: {severity}")
    if blast_radius not in BLAST_RADIUS_ORDER:
        raise ValueError(f"unknown blast radius: {blast_radius}")

    tier = _confidence_tier(confidence)

    if not safety_pass:
        return AuthorityDecision("observe", "safety gate failed")

    if active_evidence_units == 0:
        return AuthorityDecision("observe", "no active evidence remains")

    if tier == "low":
        if SEVERITY_ORDER[severity] >= SEVERITY_ORDER["high"]:
            return AuthorityDecision("validate", "high impact requires urgent validation despite low confidence")
        return AuthorityDecision("enrich", "insufficient confidence for intervention")

    if tier == "medium":
        if severity == "critical" and reversible and BLAST_RADIUS_ORDER[blast_radius] <= BLAST_RADIUS_ORDER["medium"]:
            return AuthorityDecision("mitigate", "critical impact permits bounded reversible mitigation at medium confidence")
        if SEVERITY_ORDER[severity] >= SEVERITY_ORDER["high"]:
            return AuthorityDecision("validate", "impact is material but intervention authority remains confidence-limited")
        return AuthorityDecision("enrich", "medium confidence with limited impact")

    # High confidence.
    if not reversible or blast_radius == "high":
        return AuthorityDecision("validate", "broad or irreversible action remains human/policy gated")
    if severity == "critical":
        return AuthorityDecision("isolate", "high confidence and critical impact justify bounded isolation")
    if severity == "high":
        return AuthorityDecision("mitigate", "high confidence and high impact justify reversible mitigation")
    if severity == "medium":
        return AuthorityDecision("validate", "high confidence but moderate impact")
    return AuthorityDecision("enrich", "high confidence but low operational impact")


def _case_map():
    return {case.id: case for case in build_cases()}


def evaluate_scenario(spec: dict[str, object]) -> dict[str, object]:
    case = _case_map()[str(spec["caseId"])]
    score = temporal_detector_v3(case.events, case.evaluation_minute)
    decision = remediation_authority(
        confidence=float(score["confidence"]),
        severity=str(spec["severity"]),
        reversible=bool(spec["reversible"]),
        blast_radius=str(spec["blastRadius"]),
        safety_pass=bool(spec["safetyPass"]),
        active_evidence_units=int(score["activeEvidenceUnits"]),
    )
    expected = str(spec["expectedAuthority"])
    return {
        "scenarioId": spec["id"],
        "caseId": spec["caseId"],
        "groundTruth": "incident" if case.label else "nonincident",
        "confidence": score["confidence"],
        "confidenceTier": score["tier"],
        "severity": spec["severity"],
        "reversible": spec["reversible"],
        "blastRadius": spec["blastRadius"],
        "safetyPass": spec["safetyPass"],
        "activeEvidenceUnits": score["activeEvidenceUnits"],
        "authority": decision.authority,
        "reason": decision.reason,
        "expectedAuthority": expected,
        "passed": decision.authority == expected,
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

    shared_cause_rows = [row for row in rows if row["caseId"] in {"I10", "I11", "I12"}]
    nonincident_rows = [row for row in rows if row["groundTruth"] == "nonincident"]

    checks = {
        "allFrozenAuthorityExpectationsMet": all(row["passed"] for row in rows),
        "sharedCauseIncidentsReceiveBoundedAuthority": all(row["authority"] in {"validate", "mitigate"} for row in shared_cause_rows),
        "mediumConfidenceNeverIsolatesOrRecovers": all(not (row["confidenceTier"] == "medium" and row["authority"] in {"isolate", "recover"}) for row in rows),
        "safetyFailureCapsAtObserve": all(row["authority"] == "observe" for row in rows if not row["safetyPass"]),
        "irreversibleHighBlastRadiusNeverAutoExecutes": all(row["authority"] in {"observe", "enrich", "validate"} for row in rows if (not row["reversible"] or row["blastRadius"] == "high")),
        "nonIncidentsNeverReceiveMitigateOrHigher": all(AUTHORITY_ORDER.index(row["authority"]) < AUTHORITY_ORDER.index("mitigate") for row in nonincident_rows),
        "confidenceAndSeverityRemainSeparate": any(row["caseId"] in {"I10", "I11", "I12"} and row["confidenceTier"] == "medium" and row["authority"] in {"validate", "mitigate"} for row in rows),
    }

    commit, dirty = repository_provenance()
    return {
        "lab": "SHIELD Lab #001",
        "phase": "F — confidence, severity, and remediation authority",
        "runnerVersion": RUNNER_VERSION,
        "policyVersion": POLICY_VERSION,
        "scenarioVersion": SCENARIO_VERSION,
        "temporalModelVersion": TEMPORAL_MODEL_VERSION_V3,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "phaseDigest": stable_digest(PHASE_F_SPEC),
        "temporalConfigDigest": temporal_config_digest_v3(),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "phaseConfig": PHASE_F_SPEC,
        "scenarios": rows,
        "claimChecks": checks,
        "summary": {
            "claimPasses": sum(bool(value) for value in checks.values()),
            "claimCount": len(checks),
            "allPassed": all(checks.values()),
        },
        "interpretation": (
            "Phase F tests a candidate remediation-authority policy that consumes SHIELD confidence as one input alongside severity, reversibility, blast radius, and safety. "
            "A pass means only that the committed synthetic authority scenarios satisfy the frozen policy invariants. It does not validate automated remediation in production."
        ),
        "limitations": [
            "Severity labels are synthetic policy inputs rather than measured business impact.",
            "The authority ladder is an experimental policy instrument, not a universal SHIELD requirement.",
            "No real remediation action is executed; the lab evaluates authority decisions only.",
            "Isolation and recovery semantics require system-specific safety proofs before production use.",
            "Human approval, change windows, dependency ownership, and rollback verification are not modeled.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    summary = report["summary"]
    lines = [
        "# SHIELD Lab #001 — Phase F Summary",
        "",
        f"**Overall:** {'PASS' if summary['allPassed'] else 'FAIL'}  ",
        f"**Policy:** `{report['policyVersion']}`  ",
        f"**Temporal model:** `{report['temporalModelVersion']}`  ",
        f"**Repository:** `{report['repositoryCommit']}` (dirty={report['repositoryDirty']})",
        "",
        "## Authority scenarios",
        "",
        "| ID | Case | Confidence | Severity | Safety | Authority | Expected |",
        "|---|---|---:|---|---|---|---|",
    ]
    for row in report["scenarios"]:
        lines.append(
            f"| {row['scenarioId']} | {row['caseId']} | {row['confidence']:.6f} ({row['confidenceTier']}) | "
            f"{row['severity']} | {'pass' if row['safetyPass'] else 'fail'} | {row['authority']} | {row['expectedAuthority']} |"
        )
    lines.extend(["", "## Claim checks", ""])
    for name, passed in report["claimChecks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")
    lines.extend(["", "## Interpretation", "", report["interpretation"], "", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run SHIELD Phase F remediation-authority experiment.")
    parser.add_argument("--output", default="labs/shield_001/results/phase-f-latest.json")
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
