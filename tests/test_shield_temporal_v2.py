import unittest
from unittest.mock import patch

from labs.shield_001 import phase_c, phase_c2
from labs.shield_001.temporal_v2 import (
    TEMPORAL_MODEL_VERSION_V2,
    temporal_config_digest_v2,
    temporal_detector_v2,
)
from labs.shield_001.temporal_v2_validation import build_report, render_summary


class ShieldTemporalV2Tests(unittest.TestCase):
    def test_v2_preserves_frozen_phase_c(self):
        with patch.object(phase_c, "temporal_detector", temporal_detector_v2):
            report = phase_c.build_report()
        self.assertTrue(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 7)
        self.assertEqual(
            [row["confidence"] for row in report["analyses"]["accumulation"]["profiles"]],
            [0.210363, 0.579006, 0.795933, 0.896688],
        )
        self.assertEqual(
            [row["confidence"] for row in report["analyses"]["passiveDecay"]["profiles"]],
            [0.93464, 0.744344, 0.494376, 0.288927, 0.156749],
        )

    def test_cross_fingerprint_recovery_is_isolated(self):
        with patch.object(phase_c2, "temporal_detector", temporal_detector_v2):
            result = phase_c2.cross_fingerprint_recovery_analysis()
        self.assertTrue(result["passed"])
        self.assertEqual(result["confidenceDrop"], 0.0)
        self.assertEqual(
            result["baseline"]["confidence"],
            result["withUnrelatedRecovery"]["confidence"],
        )

    def test_stale_history_does_not_amplify_current_episode(self):
        with patch.object(phase_c2, "temporal_detector", temporal_detector_v2):
            result = phase_c2.mixed_stale_history_analysis()
        self.assertTrue(result["passed"])
        self.assertEqual(result["confidenceAmplification"], 0.0)
        self.assertFalse(result["tierEscalated"])
        self.assertEqual(
            result["withStaleHistory"]["activeEpisodeFailureEvents"],
            12,
        )
        self.assertGreater(
            result["withStaleHistory"]["historicalFailureEventsExcludedFromStrength"],
            1000,
        )

    def test_future_clock_skew_is_visible_without_affecting_confidence(self):
        with patch.object(phase_c2, "temporal_detector", temporal_detector_v2):
            result = phase_c2.future_clock_skew_analysis()
        self.assertTrue(result["passed"])
        self.assertTrue(result["visibleDifference"])
        self.assertEqual(result["futureResult"]["confidence"], 0.0)
        self.assertEqual(result["futureResult"]["futureEventCount"], 12)
        self.assertEqual(result["futureResult"]["maxFutureSkewMinutes"], 2.0)

    def test_timestamp_tie_keeps_conflict_visible(self):
        with patch.object(phase_c2, "temporal_detector", temporal_detector_v2):
            result = phase_c2.timestamp_tie_analysis()
        self.assertTrue(result["passed"])
        self.assertTrue(result["distinguishable"])
        self.assertEqual(result["conflict"]["confidence"], 0.0)
        self.assertEqual(result["conflict"]["timestampConflictUnits"], 12)
        self.assertEqual(result["recoveryOnly"]["timestampConflictUnits"], 0)

    def test_all_frozen_phase_c2_checks_pass_under_v2(self):
        with patch.object(phase_c2, "temporal_detector", temporal_detector_v2):
            report = phase_c2.build_report()
        self.assertTrue(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 7)

    def test_validation_preserves_v1_failure_and_accepts_v2(self):
        report = build_report()
        self.assertTrue(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 5)
        self.assertEqual(report["results"]["phaseCV1"]["claimPasses"], 7)
        self.assertEqual(report["results"]["phaseC2V1"]["claimPasses"], 3)
        self.assertEqual(report["results"]["phaseCV2"]["claimPasses"], 7)
        self.assertEqual(report["results"]["phaseC2V2"]["claimPasses"], 7)
        summary = render_summary(report)
        self.assertIn("**Overall:** PASS", summary)
        self.assertIn("Phase C2 adversarial checks", summary)
        self.assertIn("Mixed stale-history confidence amplification: `0.000000`", summary)

    def test_v2_identity_and_digest_are_stable(self):
        self.assertEqual(TEMPORAL_MODEL_VERSION_V2, "shield-temporal-evidence-v2")
        digest = temporal_config_digest_v2()
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, temporal_config_digest_v2())


if __name__ == "__main__":
    unittest.main()
