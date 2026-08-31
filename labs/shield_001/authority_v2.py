from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .phase_f import AUTHORITY_ORDER, AuthorityDecision, remediation_authority

POLICY_VERSION_V2 = "shield-remediation-authority-policy-v2"
ENVELOPE_VERSION = "shield-authority-evidence-envelope-v1"

MAX_AGE_MINUTES = {
    "severity": 30.0,
    "reversibility": 1440.0,
    "blast_radius": 1440.0,
    "rollback": 1440.0,
    "safety": 10.0,
}


@dataclass(frozen=True)
class AuthorityEvidence:
    value: object
    source: str
    trusted: bool
    verified: bool
    age_minutes: float


@dataclass(frozen=True)
class SafetyEvidence:
    signals: tuple[bool, ...]
    source: str
    trusted: bool
    verified: bool
    age_minutes: float


@dataclass(frozen=True)
class AuthorityEvidenceEnvelope:
    severity: AuthorityEvidence
    reversibility: AuthorityEvidence
    blast_radius: AuthorityEvidence
    rollback: AuthorityEvidence
    safety: SafetyEvidence


def _fresh(evidence: AuthorityEvidence | SafetyEvidence, domain: str) -> bool:
    return evidence.age_minutes >= 0 and evidence.age_minutes <= MAX_AGE_MINUTES[domain]


def _trusted(evidence: AuthorityEvidence | SafetyEvidence, domain: str) -> bool:
    return evidence.trusted and evidence.verified and _fresh(evidence, domain)


def _cap(authority: str, maximum: str) -> str:
    return AUTHORITY_ORDER[min(AUTHORITY_ORDER.index(authority), AUTHORITY_ORDER.index(maximum))]


def _safety_consensus(safety: SafetyEvidence) -> bool:
    return (
        _trusted(safety, "safety")
        and len(safety.signals) > 0
        and all(safety.signals)
    )


def remediation_authority_v2(
    *,
    confidence: float,
    active_evidence_units: int,
    envelope: AuthorityEvidenceEnvelope,
) -> AuthorityDecision:
    """Authority policy v2 with fail-closed metadata trust semantics.

    Inputs may only increase authority when their evidence is trusted, verified,
    and fresh. Contradictory or missing safety consensus caps at observe.
    Untrusted severity/reversibility/blast-radius evidence caps at validate.
    Rollback verification is required before mitigation or isolation that relies
    on reversibility.
    """

    if not _safety_consensus(envelope.safety):
        return AuthorityDecision("observe", "authority safety evidence is untrusted, stale, unverified, or contradictory")

    severity_ok = _trusted(envelope.severity, "severity")
    reversibility_ok = _trusted(envelope.reversibility, "reversibility")
    blast_radius_ok = _trusted(envelope.blast_radius, "blast_radius")
    rollback_ok = _trusted(envelope.rollback, "rollback") and bool(envelope.rollback.value)

    # Severity, reversibility, and blast-radius metadata can expand authority.
    # If any of those inputs are not trustworthy, fail closed at validate.
    if not severity_ok or not reversibility_ok or not blast_radius_ok:
        base = remediation_authority(
            confidence=confidence,
            severity="medium",
            reversible=False,
            blast_radius="high",
            safety_pass=True,
            active_evidence_units=active_evidence_units,
        )
        return AuthorityDecision(_cap(base.authority, "validate"), "authority metadata envelope is incomplete or untrusted")

    severity = str(envelope.severity.value)
    reversible = bool(envelope.reversibility.value)
    blast_radius = str(envelope.blast_radius.value)

    base = remediation_authority(
        confidence=confidence,
        severity=severity,
        reversible=reversible,
        blast_radius=blast_radius,
        safety_pass=True,
        active_evidence_units=active_evidence_units,
    )

    # Any authority at or above mitigate that depends on a reversible action must
    # have independently verified rollback capability.
    if AUTHORITY_ORDER.index(base.authority) >= AUTHORITY_ORDER.index("mitigate"):
        if not reversible or not rollback_ok:
            return AuthorityDecision("validate", "rollback capability is not independently verified")

    return AuthorityDecision(base.authority, f"trusted authority envelope: {base.reason}")


def trusted_envelope(
    *,
    severity: str,
    reversible: bool,
    blast_radius: str,
    rollback_verified: bool = True,
    safety_signals: Iterable[bool] = (True,),
) -> AuthorityEvidenceEnvelope:
    """Test helper for a fully trusted, fresh envelope."""
    return AuthorityEvidenceEnvelope(
        severity=AuthorityEvidence(severity, "impact-service", True, True, 0.0),
        reversibility=AuthorityEvidence(reversible, "change-catalog", True, True, 0.0),
        blast_radius=AuthorityEvidence(blast_radius, "dependency-map", True, True, 0.0),
        rollback=AuthorityEvidence(rollback_verified, "rollback-verifier", True, True, 0.0),
        safety=SafetyEvidence(tuple(safety_signals), "safety-consensus", True, True, 0.0),
    )
