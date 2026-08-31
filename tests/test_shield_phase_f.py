import unittest

from labs.shield_001.phase_f import (
    AUTHORITY_ORDER,
    build_report,
    evaluate_scenario,
    remediation_authority,
)


class ShieldLab001PhaseFTests(unittest.TestCase):
    def test_frozen_authority_scenarios_pass(self):
        report = build_report()
        self.assertTrue(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 7)
        self.assertEqual(report["summary"]["claimCount"], 7)

    def test_shared_cause_false_negatives_receive_bounded_authority(self):
        report = build_report()
        rows = {row["caseId"]: row for row in report["scenarios"]}
        self.assertEqual(rows["I10"]["confidenceTier"], "medium")
        self.assertEqual(rows["I11"]["confidenceTier"], "medium")
        self.assertEqual(rows["I12"]["confidenceTier"], "medium")
        self.assertEqual(rows["I10"]["authority"], "mitigate")
        self.assertEqual(rows["I11"]["authority"], "mitigate")
        self.assertEqual(rows["I12"]["authority"], "validate")

    def test_medium_confidence_cannot_isolate_or_recover(self):
        for severity in ("low", "medium", "high", "critical"):
            decision = remediation_authority(
                confidence=0.60,
                severity=severity,
                reversible=True,
                blast_radius="low",
                safety_pass=True,
                active_evidence_units=12,
            )
            self.assertLess(
                AUTHORITY_ORDER.index(decision.authority),
                AUTHORITY_ORDER.index("isolate"),
            )

    def test_safety_failure_caps_authority_at_observe(self):
        decision = remediation_authority(
            confidence=0.95,
            severity="critical",
            reversible=True,
            blast_radius="low",
            safety_pass=False,
            active_evidence_units=12,
        )
        self.assertEqual(decision.authority, "observe")

    def test_irreversible_high_blast_radius_is_not_auto_executed(self):
        decision = remediation_authority(
            confidence=0.95,
            severity="critical",
            reversible=False,
            blast_radius="high",
            safety_pass=True,
            active_evidence_units=12,
        )
        self.assertEqual(decision.authority, "validate")

    def test_no_active_evidence_means_observe(self):
        decision = remediation_authority(
            confidence=0.0,
            severity="critical",
            reversible=True,
            blast_radius="low",
            safety_pass=True,
            active_evidence_units=0,
        )
        self.assertEqual(decision.authority, "observe")

    def test_nonincident_scenarios_never_mitigate(self):
        report = build_report()
        for row in report["scenarios"]:
            if row["groundTruth"] == "nonincident":
                self.assertLess(
                    AUTHORITY_ORDER.index(row["authority"]),
                    AUTHORITY_ORDER.index("mitigate"),
                )

    def test_expected_safety_failure_scenario_is_observe(self):
        row = evaluate_scenario({
            "id": "test",
            "caseId": "I01",
            "severity": "critical",
            "reversible": True,
            "blastRadius": "low",
            "safetyPass": False,
            "expectedAuthority": "observe",
        })
        self.assertTrue(row["passed"])


if __name__ == "__main__":
    unittest.main()
