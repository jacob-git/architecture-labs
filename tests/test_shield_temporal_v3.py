import unittest
from unittest.mock import patch

from labs.shield_001 import phase_c, phase_c2, phase_d
from labs.shield_001.temporal_v2 import temporal_detector_v2
from labs.shield_001.temporal_v3 import (
    TEMPORAL_MODEL_VERSION_V3,
    temporal_config_digest_v3,
    temporal_detector_v3,
)
from labs.shield_001.temporal_v3_validation import build_report, render_summary


class ShieldTemporalV3Tests(unittest.TestCase):
    def test_v2_phase_d_counterexamples_are_preserved(self):
        report = phase_d.build_report()
        self.assertFalse(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 5)
        failed = {
            name
            for name, passed in report["claimChecks"].items()
            if not passed
        }
        self.assertEqual(
            failed,
            {
                "mixedFingerprintsDoNotMutuallyReinforce",
                "staleDiverseUnitsCannotEscalateFreshEvidence",
            },
        )

    def test_v3_passes_frozen_phase_c(self):
        with patch.object(phase_c, "temporal_detector", temporal_detector_v3):
            report = phase_c.build_report()
        self.assertTrue(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 7)

    def test_v3_preserves_phase_c_confidence_trajectory(self):
        with patch.object(phase_c, "temporal_detector", temporal_detector_v2):
            v2 = phase_c.build_report()
        with patch.object(phase_c, "temporal_detector", temporal_detector_v3):
            v3 = phase_c.build_report()

        self.assertEqual(
            [
                row["confidence"]
                for row in v2["analyses"]["accumulation"]["profiles"]
            ],
            [
                row["confidence"]
                for row in v3["analyses"]["accumulation"]["profiles"]
            ],
        )
        self.assertEqual(
            [
                row["confidence"]
                for row in v2["analyses"]["passiveDecay"]["profiles"]
            ],
            [
                row["confidence"]
                for row in v3["analyses"]["passiveDecay"]["profiles"]
            ],
        )

    def test_v3_passes_frozen_phase_c2(self):
        with patch.object(phase_c2, "temporal_detector", temporal_detector_v3):
            report = phase_c2.build_report()
        self.assertTrue(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 7)

    def test_v3_passes_frozen_phase_d(self):
        with patch.object(
            phase_d,
            "temporal_detector_v2",
            temporal_detector_v3,
        ):
            report = phase_d.build_report()
        self.assertTrue(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 7)

        mixed = report["analyses"]["mixedFingerprint"]
        self.assertLessEqual(
            mixed["confidenceAmplification"],
            mixed["maxAllowedAmplification"],
        )
        self.assertFalse(mixed["tierEscalated"])

        stale = report["analyses"]["staleDiverseAmplification"]
        self.assertLessEqual(
            stale["confidenceAmplification"],
            stale["maxAllowedAmplification"],
        )
        self.assertFalse(stale["tierEscalated"])

    def test_v3_fingerprint_partition_is_visible(self):
        units = phase_c.build_balanced_observations(12)
        from dataclasses import replace
        from labs.shield_001.temporal_v1 import TemporalEvent

        events = [
            TemporalEvent(
                replace(unit, fingerprint="dependency-x-timeout"),
                0.0,
                "failure",
            )
            for unit in units[:6]
            for _ in range(5)
        ]
        events.extend(
            TemporalEvent(
                replace(unit, fingerprint="dependency-y-timeout"),
                0.0,
                "failure",
            )
            for unit in units[6:]
            for _ in range(5)
        )

        result = temporal_detector_v3(events, 0.0)
        self.assertEqual(result["detector"], TEMPORAL_MODEL_VERSION_V3)
        self.assertEqual(result["fingerprintCount"], 2)
        self.assertEqual(result["activeFingerprintCount"], 2)
        self.assertIn(result["selectedFingerprint"], result["fingerprintScores"])
        self.assertEqual(
            result["confidence"],
            max(
                item["confidence"]
                for item in result["fingerprintScores"].values()
            ),
        )

    def test_validation_report_is_explicit(self):
        report = build_report()
        self.assertTrue(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 6)
        self.assertEqual(report["summary"]["claimCount"], 6)
        self.assertTrue(report["results"]["phaseDV3"]["allPassed"])
        summary = render_summary(report)
        self.assertIn("**Overall:** PASS", summary)
        self.assertIn("Phase D holdout", summary)
        self.assertIn("mixed-fingerprint", summary.lower())

    def test_v3_config_digest_is_stable_sha256(self):
        digest = temporal_config_digest_v3()
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, temporal_config_digest_v3())


if __name__ == "__main__":
    unittest.main()
