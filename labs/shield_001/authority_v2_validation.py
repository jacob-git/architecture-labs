from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .authority_v2 import (
    ENVELOPE_VERSION,
    POLICY_VERSION_V2,
    AuthorityEvidence,
    AuthorityEvidenceEnvelope,
    SafetyEvidence,
    remediation_authority_v2,
    trusted_envelope,
)
from .core import stable_digest
from .phase_e import build_cases
from .phase_f import AUTHORITY_ORDER, POLICY_VERSION, SCENARIOS as PHASE_F_SCENARIOS, build_report as build_phase_f_v1
from .phase_f2 import SCENARIOS as PHASE_F2_SCENARIOS, build_report as build_phase_f2_v1
from .temporal_v3 import TEMPORAL_MODEL_VERSION_V3, temporal_config_digest_v3, temporal_detector_v3

RUNNER_VERSION = "shield-authority-v2-validation-runner-v1"
VALIDATION_VERSION = "shield-authority-v2-frozen-f-f2-validation-v1"


def _case_map():
    return {case.id: case for case in build_cases()}


def _score_case(case_id: str) -> dict[str, object]:
    case = _case_map()[case_id]
    return temporal_detector_v3(case.events, case.evaluation_minute)


def _phase_f_v2_rows() -> list[dict[str, object]]:
    rows = []
    for spec in PHASE_F_SCENARIOS:
        score = _score_case(str(spec["caseId"]))
        envelope = trusted_envelope(
            severity=str(spec["severity"]),
            reversible=bool(spec["reversible"]),
            blast_radius=str(spec["blastRadius"]),
            rollback_verified=True,
            safety_signals=(bool(spec["safetyPass"]),),
        )
        decision = remediation_authority_v2(
            confidence=float(score["confidence"]),
            active_evidence_units=int(score["activeEvidenceUnits"]),
            envelope=envelope,
        )
        expected = str(spec["expectedAuthority"])
        rows.append({
            "scenarioId": spec["id"],
            "caseId": spec["caseId"],
            "authority": decision.authority,
            "expectedAuthority": expected,
            "passed": decision.authority == expected,
        })
    return rows


def _evidence(value: object, *, trusted: bool = True, verified: bool = True, age: float = 0.0, source: str = "test-source") -> AuthorityEvidence:
    return AuthorityEvidence(value, source, trusted, verified, age)


def _f2_envelope(spec: dict[str, object]) -> AuthorityEvidenceEnvelope:
    declared = dict(spec["declared"])
    truth = dict(spec["truth"])

    severity_trusted = bool(truth.get("severityTrusted", True))
    severity_age = float(truth.get("impactAgeMinutes", 0.0))

    reversibility_verified = bool(truth.get("reversibleVerified", True))
    blast_verified = bool(truth.get("blastRadiusVerified", True))
    rollback_verified = bool(truth.get("rollbackVerified", True))

    safety_signals = tuple(bool(value) for value in truth.get("safetySignals", [bool(declared["safetyPass"])]))
    safety_consensus = bool(truth.get("safetyConsensus", all(safety_signals)))

    return AuthorityEvidenceEnvelope(
        severity=_evidence(
            declared["severity"],
            trusted=severity_trusted,
            verified=severity_trusted,
            age=severity_age,
            source="impact-evidence",
        ),
        reversibility=_evidence(
            declared["reversible"],
            trusted=True,
            verified=reversibility_verified,
            source="reversibility-evidence",
        ),
        blast_radius=_evidence(
            declared["blastRadius"],
            trusted=True,
            verified=blast_verified,
            source="blast-radius-evidence",
        ),
        rollback=_evidence(
            rollback_verified,
            trusted=True,
            verified=rollback_verified,
            source="rollback-verifier",
        ),
        safety=SafetyEvidence(
            signals=safety_signals,
            source="safety-consensus",
            trusted=True,
            verified=safety_consensus,
            age_minutes=0.0,
        ),
    )


def _phase_f2_v2_rows() -> list[dict[str, object]]:
    rows = []
    for spec in PHASE_F2_SCENARIOS:
        score = _score_case(str(spec["caseId"]))
        decision = remediation_authority_v2(
            confidence=float(score["confidence"]),
            active_evidence_units=int(score["activeEvidenceUnits"]),
            envelope=_f2_envelope(spec),
        )
        maximum = str(spec["maximumSafeAuthority"])
        passed = AUTHORITY_ORDER.index(decision.authority) <= AUTHORITY_ORDER.index(maximum)
        rows.append({
            "scenarioId": spec["id"],
            "caseId": spec["caseId"],
            "authority": decision.authority,
            "maximumSafeAuthority": maximum,
            "passed": passed,
        })
    return rows


def repository_provenance() -> tuple[str, bool | None]:
    root = Path(__file__).resolve().parents[2]
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=root, check=True, capture_output=True, text=True).stdout.strip())
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return "unknown", None


def build_report() -> dict[str, object]:
    phase_f_v1 = build_phase_f_v1()
    phase_f2_v1 = build_phase_f2_v1()
    phase_f_v2 = _phase_f_v2_rows()
    phase_f2_v2 = _phase_f2_v2_rows()

    expected_v1_f2_failures = {"F2-01", "F2-02", "F2-03", "F2-04", "F2-05", "F2-06"}
    actual_v1_f2_failures = set(phase_f2_v1["failedScenarioIds"])

    checks = {
        "v1PhaseFBaselinePreserved": phase_f_v1["summary"]["allPassed"],
        "v1PhaseF2FailurePreserved": (
            phase_f2_v1["summary"]["claimPasses"] == 1
            and phase_f2_v1["summary"]["claimCount"] == 7
            and actual_v1_f2_failures == expected_v1_f2_failures
        ),
        "v2PassesFrozenPhaseF": all(row["passed"] for row in phase_f_v2),
        "v2PassesFrozenPhaseF2": all(row["passed"] for row in phase_f2_v2),
        "frozenScenarioCountsPreserved": len(phase_f_v2) == 10 and len(phase_f2_v2) == 7,
    }

    commit, dirty = repository_provenance()
    return {
        "lab": "SHIELD Lab #001",
        "phase": "Authority policy v2 validation against frozen Phase F and F2",
        "runnerVersion": RUNNER_VERSION,
        "validationVersion": VALIDATION_VERSION,
        "authorityPolicyV1": POLICY_VERSION,
        "authorityPolicyV2": POLICY_VERSION_V2,
        "authorityEnvelopeVersion": ENVELOPE_VERSION,
        "temporalModelVersion": TEMPORAL_MODEL_VERSION_V3,
        "repositoryCommit": commit,
        "repositoryDirty": dirty,
        "phaseFScenarioDigest": stable_digest(PHASE_F_SCENARIOS),
        "phaseF2ScenarioDigest": stable_digest(PHASE_F2_SCENARIOS),
        "temporalConfigDigest": temporal_config_digest_v3(),
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "results": {
            "phaseFV1": phase_f_v1["summary"],
            "phaseF2V1": phase_f2_v1["summary"],
            "phaseFV2": {"passes": sum(row["passed"] for row in phase_f_v2), "count": len(phase_f_v2), "rows": phase_f_v2},
            "phaseF2V2": {"passes": sum(row["passed"] for row in phase_f2_v2), "count": len(phase_f2_v2), "rows": phase_f2_v2},
        },
        "claimChecks": checks,
        "summary": {
            "claimPasses": sum(bool(value) for value in checks.values()),
            "claimCount": len(checks),
            "allPassed": all(checks.values()),
        },
        "interpretation": (
            "Authority policy v2 is regression-accepted only if the frozen Phase F v1 behavior remains reproducible, "
            "the Phase F2 v1 trust-boundary failure remains reproducible, and the v2 Authority Evidence Envelope "
            "passes both unchanged scenario suites. This is repair evidence, not production authorization."
        ),
        "limitations": [
            "Envelope trust and verification flags are synthetic assertions rather than cryptographic attestations.",
            "Freshness windows are experimental policy parameters and are not production recommendations.",
            "Safety consensus is modeled as all required boolean signals agreeing; real systems need source identity, quorum, and policy semantics.",
            "No remediation action is executed.",
        ],
    }


def render_summary(report: dict[str, object]) -> str:
    summary = report["summary"]
    results = report["results"]
    lines = [
        "# SHIELD Lab #001 — Authority Policy V2 Validation",
        "",
        f"**Overall:** {'PASS' if summary['allPassed'] else 'FAIL'}  ",
        f"**Policy v1:** `{report['authorityPolicyV1']}`  ",
        f"**Policy v2:** `{report['authorityPolicyV2']}`  ",
        f"**Envelope:** `{report['authorityEnvelopeVersion']}`  ",
        f"**Repository:** `{report['repositoryCommit']}` (dirty={report['repositoryDirty']})",
        "",
        "| Suite | V1 | V2 |",
        "|---|---:|---:|",
        f"| Phase F | {results['phaseFV1']['claimPasses']}/{results['phaseFV1']['claimCount']} | {results['phaseFV2']['passes']}/{results['phaseFV2']['count']} |",
        f"| Phase F2 | {results['phaseF2V1']['claimPasses']}/{results['phaseF2V1']['claimCount']} | {results['phaseF2V2']['passes']}/{results['phaseF2V2']['count']} |",
        "",
        "## Claim checks",
        "",
    ]
    for name, passed in report["claimChecks"].items():
        lines.append(f"- {'PASS' if passed else 'FAIL'} — `{name}`")
    lines.extend(["", "## Interpretation", "", report["interpretation"], "", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate SHIELD authority policy v2 against frozen Phase F and F2.")
    parser.add_argument("--output", default="labs/shield_001/results/authority-v2-validation-latest.json")
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
