import unittest

from labs.shield_001.phase_b import build_observations, concentration_analysis
from labs.shield_001.scoring_v2 import effective_source_count
from labs.shield_001.v2_validation import (
    adversarial_ranking_analysis_v2,
    concentration_analysis_v2,
    evaluate_phase_a_v2,
    matrix_profiles_v2,
    monotonicity_analysis,
    volume_saturation_analysis_v2,
)


class ShieldLab001V2Tests(unittest.TestCase):
    def test_effective_source_count_distinguishes_balance_from_concentration(self):
        balanced = build_observations(
            events=500,
            apps=20,
            regions=3,
            clusters=4,
            gateways=4,
            paths=4,
            gateway_concentration=0.25,
            path_concentration=0.25,
        )
        concentrated = build_observations(
            events=500,
            apps=20,
            regions=3,
            clusters=4,
            gateways=4,
            paths=4,
            gateway_concentration=0.99,
            path_concentration=0.99,
        )
        self.assertAlmostEqual(effective_source_count(balanced, "gateway"), 4.0, places=6)
        self.assertLess(effective_source_count(concentrated, "gateway"), 1.1)

    def test_v2_preserves_all_phase_a_scenarios(self):
        phase_a = evaluate_phase_a_v2()
        self.assertTrue(phase_a["allPassed"])
        self.assertEqual(phase_a["scenarioPasses"], 3)

    def test_v2_uses_the_same_1782_profile_phase_b_matrix(self):
        rows = matrix_profiles_v2()
        self.assertEqual(len(rows), 1782)
        analysis = monotonicity_analysis(rows)
        self.assertEqual(analysis["violationCount"], 0)

    def test_v2_repairs_partial_correlation_sensitivity(self):
        v1 = concentration_analysis()
        v2 = concentration_analysis_v2()
        self.assertFalse(v1["passed"])
        self.assertTrue(v2["passed"])
        self.assertEqual(v2["strictDecreaseSteps"], 4)
        self.assertGreaterEqual(v2["balancedToConcentratedDrop"], 0.10)

    def test_v2_preserves_repetition_saturation(self):
        analysis = volume_saturation_analysis_v2()
        self.assertTrue(analysis["passed"])
        self.assertLessEqual(
            analysis["gainFrom100To10000"],
            analysis["maxAllowedGain"],
        )

    def test_v2_repairs_adversarial_ranking(self):
        analysis = adversarial_ranking_analysis_v2()
        self.assertTrue(analysis["passed"])
        self.assertLess(analysis["confidenceDelta"], 0.0)
        self.assertLess(
            analysis["highVolumeConcentrated"]["confidence"],
            analysis["independent"]["confidence"],
        )


if __name__ == "__main__":
    unittest.main()
