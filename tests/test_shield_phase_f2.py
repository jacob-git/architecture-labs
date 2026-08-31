import unittest

from labs.shield_001.phase_f2 import (
    SCENARIOS,
    build_report,
    evaluate_scenario,
    render_summary,
)


class ShieldPhaseF2Tests(unittest.TestCase):
    def test_adversarial_suite_preserves_negative_result(self):
        report = build_report()
        self.assertFalse(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 1)
        self.assertEqual(report["summary"]["claimCount"], 7)
        self.assertEqual(
            report["failedScenarioIds"],
            ["F2-01", "F2-02", "F2-03", "F2-04", "F2-05", "F2-06"],
        )

    def test_spoofed_severity_can_over_authorize_nonincident(self):
        row = evaluate_scenario(SCENARIOS[0])
        self.assertEqual(row["groundTruth"], "nonincident")
        self.assertEqual(row["authority"], "mitigate")
        self.assertEqual(row["maximumSafeAuthority"], "validate")
        self.assertFalse(row["passed"])

    def test_unverified_reversibility_can_over_authorize(self):
        row = evaluate_scenario(SCENARIOS[1])
        self.assertEqual(row["authority"], "mitigate")
        self.assertFalse(row["passed"])

    def test_unverified_blast_radius_can_over_authorize(self):
        row = evaluate_scenario(SCENARIOS[2])
        self.assertEqual(row["authority"], "mitigate")
        self.assertFalse(row["passed"])

    def test_stale_impact_can_over_authorize(self):
        row = evaluate_scenario(SCENARIOS[3])
        self.assertEqual(row["authority"], "mitigate")
        self.assertFalse(row["passed"])

    def test_contradictory_safety_can_over_authorize(self):
        row = evaluate_scenario(SCENARIOS[4])
        self.assertEqual(row["authority"], "isolate")
        self.assertEqual(row["maximumSafeAuthority"], "observe")
        self.assertFalse(row["passed"])

    def test_unverified_rollback_can_over_authorize(self):
        row = evaluate_scenario(SCENARIOS[5])
        self.assertEqual(row["authority"], "mitigate")
        self.assertFalse(row["passed"])

    def test_explicit_safety_failure_remains_fail_closed(self):
        row = evaluate_scenario(SCENARIOS[6])
        self.assertEqual(row["authority"], "observe")
        self.assertTrue(row["passed"])

    def test_summary_is_explicit_about_failure(self):
        summary = render_summary(build_report())
        self.assertIn("**Overall:** FAIL", summary)
        self.assertIn("F2-05", summary)
        self.assertIn("contradictorySafetyFailsClosed", summary)


if __name__ == "__main__":
    unittest.main()
