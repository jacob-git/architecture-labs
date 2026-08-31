import unittest

from labs.shield_001.phase_e import (
    ACCEPTANCE,
    build_cases,
    build_report,
    render_summary,
)


class ShieldLab001PhaseETests(unittest.TestCase):
    def test_corpus_is_balanced_and_deterministic(self):
        cases = build_cases()
        self.assertEqual(len(cases), 24)
        self.assertEqual(sum(case.label == 1 for case in cases), 12)
        self.assertEqual(sum(case.label == 0 for case in cases), 12)
        self.assertEqual([case.id for case in cases[:3]], ["I01", "I02", "I03"])
        self.assertEqual([case.id for case in cases[-3:]], ["N10", "N11", "N12"])

    def test_frozen_high_confidence_boundary_is_used(self):
        self.assertEqual(ACCEPTANCE["classification_threshold"], 0.75)

    def test_phase_e_preserves_expected_confusion_matrix(self):
        report = build_report()
        metrics = report["metrics"]["classification"]
        self.assertEqual(metrics["truePositive"], 9)
        self.assertEqual(metrics["falsePositive"], 0)
        self.assertEqual(metrics["trueNegative"], 12)
        self.assertEqual(metrics["falseNegative"], 3)
        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["recall"], 0.75)
        self.assertEqual(metrics["falsePositiveRate"], 0.0)

    def test_shared_cause_true_incidents_are_the_false_negatives(self):
        report = build_report()
        missed = {
            row["caseId"]
            for row in report["cases"]
            if row["label"] == 1 and not row["predictedIncident"]
        }
        self.assertEqual(missed, {"I10", "I11", "I12"})

    def test_calibration_diagnostics_are_recorded(self):
        report = build_report()
        calibration = report["metrics"]["calibration"]
        self.assertLessEqual(
            calibration["brierScore"],
            ACCEPTANCE["maximum_brier_score"],
        )
        self.assertLessEqual(
            calibration["expectedCalibrationError"],
            ACCEPTANCE["maximum_expected_calibration_error"],
        )
        self.assertGreater(len(calibration["bins"]), 0)

    def test_time_to_confidence_reports_missed_incidents(self):
        report = build_report()
        timing = report["metrics"]["timeToConfidence"]
        self.assertEqual(timing["detectedIncidentCount"], 9)
        self.assertEqual(timing["missedIncidentCount"], 3)
        self.assertEqual(timing["missedCaseIds"], ["I10", "I11", "I12"])
        self.assertEqual(timing["medianTimeToHighMinutes"], 0.0)
        self.assertEqual(timing["maximumTimeToHighMinutes"], 15.0)

    def test_phase_e_is_a_preserved_negative_result(self):
        report = build_report()
        self.assertFalse(report["summary"]["allPassed"])
        self.assertEqual(report["summary"]["claimPasses"], 6)
        self.assertEqual(report["summary"]["claimCount"], 7)
        self.assertFalse(report["claimChecks"]["recallAtLeast80Percent"])
        self.assertTrue(report["claimChecks"]["precisionAtLeast90Percent"])

    def test_summary_is_explicit_about_failure(self):
        report = build_report()
        summary = render_summary(report)
        self.assertIn("**Overall:** FAIL", summary)
        self.assertIn("Precision", summary)
        self.assertIn("Recall", summary)
        self.assertIn("I10", summary)
        self.assertIn("I11", summary)
        self.assertIn("I12", summary)


if __name__ == "__main__":
    unittest.main()
