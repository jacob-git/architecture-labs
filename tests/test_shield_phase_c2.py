import unittest

from labs.shield_001.phase_c2 import (
    build_report,
    bursty_single_unit_analysis,
    contradictory_order_analysis,
    cross_fingerprint_recovery_analysis,
    future_clock_skew_analysis,
    mixed_stale_history_analysis,
    out_of_order_recovery_analysis,
    render_summary,
    timestamp_tie_analysis,
)


class ShieldLab001PhaseC2Tests(unittest.TestCase):
    def test_cross_fingerprint_recovery_counterexample_is_detected(self):
        result = cross_fingerprint_recovery_analysis()
        self.assertFalse(result["passed"])
        self.assertGreater(result["confidenceDrop"], 0.80)
        self.assertEqual(result["withUnrelatedRecovery"]["confidence"], 0.0)

    def test_mixed_stale_history_amplification_is_detected(self):
        result = mixed_stale_history_analysis()
        self.assertFalse(result["passed"])
        self.assertGreater(result["confidenceAmplification"], 0.20)
        self.assertTrue(result["tierEscalated"])

    def test_delayed_recovery_does_not_erase_newer_failure(self):
        result = out_of_order_recovery_analysis()
        self.assertTrue(result["passed"])
        self.assertEqual(result["chronological"], result["delayedRecoveryArrival"])
        self.assertEqual(result["delayedRecoveryArrival"]["tier"], "high")

    def test_bursty_single_unit_recurrence_stays_low(self):
        result = bursty_single_unit_analysis()
        self.assertTrue(result["passed"])
        self.assertEqual(result["profile"]["tier"], "low")
        self.assertEqual(result["profile"]["activeEvidenceUnits"], 1)

    def test_future_clock_skew_is_currently_silent(self):
        result = future_clock_skew_analysis()
        self.assertFalse(result["passed"])
        self.assertFalse(result["visibleDifference"])
        self.assertEqual(result["futureResult"], result["emptyResult"])

    def test_timestamp_tie_hides_contradiction_in_temporal_v1(self):
        result = timestamp_tie_analysis()
        self.assertFalse(result["passed"])
        self.assertFalse(result["distinguishable"])
        self.assertEqual(result["conflict"], result["recoveryOnly"])

    def test_contradictory_history_remains_order_invariant(self):
        result = contradictory_order_analysis()
        self.assertTrue(result["passed"])
        self.assertEqual(result["forward"], result["reversed"])

    def test_report_preserves_negative_result(self):
        report = build_report()
        self.assertFalse(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 3)
        self.assertEqual(report["summary"]["claimCount"], 7)
        summary = render_summary(report)
        self.assertIn("**Overall:** FAIL", summary)
        self.assertIn("Cross-fingerprint recovery", summary)
        self.assertIn("Mixed stale history", summary)
        self.assertIn("Same-timestamp failure/recovery", summary)


if __name__ == "__main__":
    unittest.main()
