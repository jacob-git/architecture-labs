import unittest

from labs.shield_001.phase_c import (
    accumulation_analysis,
    build_report,
    input_order_analysis,
    partial_recovery_analysis,
    passive_decay_analysis,
    recurrence_analysis,
    render_summary,
    stale_volume_analysis,
)
from labs.shield_001.temporal_v1 import temporal_config_digest


class ShieldLab001PhaseCTests(unittest.TestCase):
    def test_fresh_independent_evidence_accumulates(self):
        analysis = accumulation_analysis()
        self.assertTrue(analysis["passed"])
        rows = analysis["profiles"]
        self.assertEqual([row["tier"] for row in rows], ["low", "medium", "high", "high"])
        confidences = [row["confidence"] for row in rows]
        self.assertTrue(
            all(higher > lower for lower, higher in zip(confidences, confidences[1:]))
        )

    def test_passive_evidence_decays_without_new_failures(self):
        analysis = passive_decay_analysis()
        self.assertTrue(analysis["passed"])
        rows = analysis["profiles"]
        self.assertEqual(rows[0]["tier"], "high")
        self.assertEqual(rows[-1]["tier"], "low")
        self.assertEqual(rows[1]["freshnessFactor"], 0.5)
        self.assertEqual(rows[2]["freshnessFactor"], 0.25)

    def test_partial_recovery_materially_reduces_confidence(self):
        analysis = partial_recovery_analysis()
        self.assertTrue(analysis["passed"])
        self.assertGreaterEqual(
            analysis["confidenceDrop"],
            analysis["minimumRequiredDrop"],
        )
        self.assertLess(
            analysis["withRecovery"]["confidence"],
            analysis["withoutRecovery"]["confidence"],
        )

    def test_full_recovery_clears_and_recurrence_rebuilds(self):
        analysis = recurrence_analysis()
        self.assertTrue(analysis["passed"])
        self.assertEqual(analysis["afterRecovery"]["confidence"], 0.0)
        self.assertEqual(analysis["beforeRecurrence"]["confidence"], 0.0)
        self.assertEqual(analysis["atRecurrence"]["tier"], "high")

    def test_large_stale_volume_cannot_override_decay(self):
        analysis = stale_volume_analysis()
        self.assertTrue(analysis["passed"])
        self.assertEqual(analysis["profile"]["activeFailureEvents"], 5000)
        self.assertEqual(analysis["profile"]["tier"], "low")

    def test_temporal_scoring_is_input_order_invariant(self):
        analysis = input_order_analysis()
        self.assertTrue(analysis["passed"])
        self.assertEqual(
            analysis["forwardConfidence"],
            analysis["reversedConfidence"],
        )

    def test_phase_c_report_and_summary_are_explicit(self):
        report = build_report()
        self.assertTrue(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 7)
        self.assertEqual(report["summary"]["claimCount"], 7)
        summary = render_summary(report)
        self.assertIn("**Overall:** PASS", summary)
        self.assertIn("staleVolumeCannotOverrideDecay", summary)
        self.assertIn("Partial recovery confidence drop", summary)

    def test_temporal_config_digest_is_stable_sha256(self):
        digest = temporal_config_digest()
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, temporal_config_digest())


if __name__ == "__main__":
    unittest.main()
