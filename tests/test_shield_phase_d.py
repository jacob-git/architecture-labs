import unittest

from labs.shield_001.phase_d import (
    build_report,
    delayed_pre_recovery_replay_analysis,
    future_data_isolation_analysis,
    mixed_fingerprint_analysis,
    recurrence_reset_analysis,
    repeated_recovery_idempotence_analysis,
    render_summary,
    stale_diverse_amplification_analysis,
    time_translation_analysis,
)


class ShieldLab001PhaseDTests(unittest.TestCase):
    def test_mixed_fingerprint_holdout_detects_cross_incident_reinforcement(self):
        result = mixed_fingerprint_analysis()
        self.assertFalse(result["passed"])
        self.assertEqual(result["fingerprintA"]["tier"], "medium")
        self.assertEqual(result["fingerprintB"]["tier"], "medium")
        self.assertEqual(result["combined"]["tier"], "high")
        self.assertGreater(result["confidenceAmplification"], 0.30)

    def test_stale_diverse_units_can_escalate_fresh_evidence(self):
        result = stale_diverse_amplification_analysis()
        self.assertFalse(result["passed"])
        self.assertEqual(result["freshOnly"]["tier"], "medium")
        self.assertEqual(result["withStaleDiversity"]["tier"], "high")
        self.assertGreater(result["confidenceAmplification"], 0.30)

    def test_time_translation_is_invariant(self):
        self.assertTrue(time_translation_analysis()["passed"])

    def test_delayed_pre_recovery_replay_is_ignored(self):
        self.assertTrue(delayed_pre_recovery_replay_analysis()["passed"])

    def test_repeated_recovery_is_idempotent(self):
        self.assertTrue(repeated_recovery_idempotence_analysis()["passed"])

    def test_future_telemetry_is_visible_but_does_not_change_current_score(self):
        result = future_data_isolation_analysis()
        self.assertTrue(result["passed"])
        self.assertTrue(result["scoreFieldsEqual"])
        self.assertGreater(result["withFutureTelemetry"]["futureEventCount"], 0)

    def test_recurrence_after_recovery_starts_from_fresh_state(self):
        self.assertTrue(recurrence_reset_analysis()["passed"])

    def test_report_preserves_holdout_failure(self):
        report = build_report()
        self.assertFalse(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 5)
        self.assertEqual(report["summary"]["claimCount"], 7)
        summary = render_summary(report)
        self.assertIn("**Overall:** FAIL", summary)
        self.assertIn("mixedFingerprintsDoNotMutuallyReinforce", summary)
        self.assertIn("staleDiverseUnitsCannotEscalateFreshEvidence", summary)


if __name__ == "__main__":
    unittest.main()
