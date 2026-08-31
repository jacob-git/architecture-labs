import unittest

from labs.aeg_shield_001.phase_e import run_phase_e


class AEGShieldPhaseETest(unittest.TestCase):
    def test_feedback_memory_v3_repairs_frozen_failure_classes(self):
        result = run_phase_e()
        self.assertEqual(result["checks_total"], 10)
        self.assertEqual(result["checks_passed"], 10)
        self.assertTrue(result["repair_validated"])
        self.assertEqual(
            [check["scenario"] for check in result["checks"]],
            [
                "phase_a_learning_preserved",
                "stale_evidence",
                "environment_contamination",
                "poisoned_feedback",
                "bounded_aggregation",
                "future_timestamp",
                "correlation_id_evasion",
                "replay_with_new_ids",
                "trusted_producer_compromise",
                "verified_counterevidence",
            ],
        )
        self.assertTrue(all(check["passed"] for check in result["checks"]))


if __name__ == "__main__":
    unittest.main()
