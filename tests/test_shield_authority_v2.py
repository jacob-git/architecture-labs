from __future__ import annotations

import unittest

from labs.shield_001.authority_v2 import (
    AuthorityEvidence,
    AuthorityEvidenceEnvelope,
    SafetyEvidence,
    remediation_authority_v2,
    trusted_envelope,
)
from labs.shield_001.authority_v2_validation import build_report


class AuthorityV2Tests(unittest.TestCase):
    def test_trusted_critical_medium_can_mitigate(self) -> None:
        decision = remediation_authority_v2(
            confidence=0.62,
            active_evidence_units=12,
            envelope=trusted_envelope(
                severity="critical",
                reversible=True,
                blast_radius="low",
                rollback_verified=True,
            ),
        )
        self.assertEqual(decision.authority, "mitigate")

    def test_untrusted_severity_caps_at_validate(self) -> None:
        envelope = trusted_envelope(
            severity="critical",
            reversible=True,
            blast_radius="low",
        )
        envelope = AuthorityEvidenceEnvelope(
            severity=AuthorityEvidence("critical", "impact", False, False, 0.0),
            reversibility=envelope.reversibility,
            blast_radius=envelope.blast_radius,
            rollback=envelope.rollback,
            safety=envelope.safety,
        )
        decision = remediation_authority_v2(confidence=0.62, active_evidence_units=12, envelope=envelope)
        self.assertLessEqual(["observe", "enrich", "validate"].index(decision.authority), 2)
        self.assertEqual(decision.authority, "validate")

    def test_stale_severity_caps_at_validate(self) -> None:
        envelope = trusted_envelope(severity="critical", reversible=True, blast_radius="low")
        envelope = AuthorityEvidenceEnvelope(
            severity=AuthorityEvidence("critical", "impact", True, True, 90.0),
            reversibility=envelope.reversibility,
            blast_radius=envelope.blast_radius,
            rollback=envelope.rollback,
            safety=envelope.safety,
        )
        decision = remediation_authority_v2(confidence=0.62, active_evidence_units=12, envelope=envelope)
        self.assertEqual(decision.authority, "validate")

    def test_contradictory_safety_fails_closed(self) -> None:
        envelope = trusted_envelope(severity="critical", reversible=True, blast_radius="low")
        envelope = AuthorityEvidenceEnvelope(
            severity=envelope.severity,
            reversibility=envelope.reversibility,
            blast_radius=envelope.blast_radius,
            rollback=envelope.rollback,
            safety=SafetyEvidence((True, False), "safety", True, True, 0.0),
        )
        decision = remediation_authority_v2(confidence=0.95, active_evidence_units=12, envelope=envelope)
        self.assertEqual(decision.authority, "observe")

    def test_unverified_reversibility_or_blast_radius_caps_at_validate(self) -> None:
        trusted = trusted_envelope(severity="critical", reversible=True, blast_radius="low")
        for envelope in (
            AuthorityEvidenceEnvelope(
                trusted.severity,
                AuthorityEvidence(True, "change", True, False, 0.0),
                trusted.blast_radius,
                trusted.rollback,
                trusted.safety,
            ),
            AuthorityEvidenceEnvelope(
                trusted.severity,
                trusted.reversibility,
                AuthorityEvidence("low", "map", True, False, 0.0),
                trusted.rollback,
                trusted.safety,
            ),
        ):
            with self.subTest(envelope=envelope):
                decision = remediation_authority_v2(confidence=0.95, active_evidence_units=12, envelope=envelope)
                self.assertEqual(decision.authority, "validate")

    def test_unverified_rollback_blocks_mitigation(self) -> None:
        envelope = trusted_envelope(
            severity="critical",
            reversible=True,
            blast_radius="low",
            rollback_verified=False,
        )
        decision = remediation_authority_v2(confidence=0.62, active_evidence_units=12, envelope=envelope)
        self.assertEqual(decision.authority, "validate")

    def test_frozen_f_and_f2_validation_passes_v2(self) -> None:
        report = build_report()
        self.assertTrue(report["claimChecks"]["v1PhaseFBaselinePreserved"])
        self.assertTrue(report["claimChecks"]["v1PhaseF2FailurePreserved"])
        self.assertTrue(report["claimChecks"]["v2PassesFrozenPhaseF"])
        self.assertTrue(report["claimChecks"]["v2PassesFrozenPhaseF2"])
        self.assertTrue(report["summary"]["allPassed"])


if __name__ == "__main__":
    unittest.main()
