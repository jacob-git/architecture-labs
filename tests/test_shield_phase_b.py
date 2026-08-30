import unittest

from labs.shield_001.phase_b import (
    adversarial_ranking_analysis,
    concentration_analysis,
    matrix_profiles,
    monotonicity_analysis,
    render_summary,
    volume_saturation_analysis,
)


class ShieldLab001PhaseBTests(unittest.TestCase):
    def test_matrix_is_deterministic_and_large_enough_to_stress_v1(self):
        rows = matrix_profiles()
        self.assertEqual(len(rows), 1782)
        self.assertEqual(rows[0]["profile"]["events"], 10)
        self.assertEqual(rows[-1]["profile"]["events"], 2000)

    def test_topology_cardinality_is_monotonic_in_v1(self):
        analysis = monotonicity_analysis(matrix_profiles())
        self.assertGreater(analysis["comparisons"], 0)
        self.assertEqual(analysis["violationCount"], 0)

    def test_phase_b_detects_concentration_blindness_in_v1(self):
        analysis = concentration_analysis()
        self.assertFalse(analysis["passed"])
        self.assertEqual(analysis["balancedToConcentratedDrop"], 0.0)
        self.assertEqual(analysis["strictDecreaseSteps"], 0)
        confidences = [row["confidence"] for row in analysis["profiles"]]
        self.assertEqual(len(set(confidences)), 1)

    def test_repetition_remains_saturated_after_100_events(self):
        analysis = volume_saturation_analysis()
        self.assertTrue(analysis["passed"])
        self.assertLessEqual(
            analysis["gainFrom100To10000"],
            analysis["maxAllowedGain"],
        )

    def test_phase_b_detects_adversarial_ranking_inversion(self):
        analysis = adversarial_ranking_analysis()
        self.assertFalse(analysis["passed"])
        self.assertGreater(analysis["confidenceDelta"], 0.0)
        self.assertGreater(
            analysis["highVolumeConcentrated"]["confidence"],
            analysis["independent"]["confidence"],
        )

    def test_summary_makes_negative_result_explicit(self):
        concentration = concentration_analysis()
        ranking = adversarial_ranking_analysis()
        report = {
            "scoringVersion": "shield-evidence-score-v1",
            "repositoryCommit": "abc123",
            "repositoryDirty": False,
            "sweepDigest": "sweep",
            "scoringConfigDigest": "score",
            "matrix": {"profilesEvaluated": 1782},
            "analyses": {
                "monotonicity": {"violationCount": 0},
                "partialCorrelation": concentration,
                "volumeSaturation": volume_saturation_analysis(),
                "adversarialRanking": ranking,
            },
            "claimChecks": {
                "topologyMonotonicity": True,
                "postSaturationVolumeBounded": True,
                "partialCorrelationSensitivity": False,
                "adversarialRanking": False,
            },
            "summary": {"allPassed": False},
            "interpretation": "Negative results are evidence.",
            "limitations": ["Synthetic."],
        }
        summary = render_summary(report)
        self.assertIn("**Overall:** FAIL", summary)
        self.assertIn("partialCorrelationSensitivity", summary)
        self.assertIn("Adversarial ranking delta", summary)


if __name__ == "__main__":
    unittest.main()
