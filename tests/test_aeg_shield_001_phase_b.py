import unittest

from labs.aeg_shield_001.phase_b import run_phase_b


class AEGShieldPhaseBTests(unittest.TestCase):
    def test_feedback_memory_v1_fails_all_four_adversarial_checks(self):
        result = run_phase_b()
        self.assertEqual(result["checks_total"], 4)
        self.assertEqual(result["checks_passed"], 0)
        self.assertFalse(result["feedback_v1_survived"])
        self.assertEqual(
            [check["scenario"] for check in result["checks"]],
            [
                "stale_evidence",
                "correlated_incidents",
                "environment_contamination",
                "poisoned_feedback",
            ],
        )
        self.assertTrue(all(check["actual"] == "deny" for check in result["checks"]))
        self.assertTrue(all(check["expected"] == "allow" for check in result["checks"]))


if __name__ == "__main__":
    unittest.main()
