import unittest

from labs.aeg_shield_001.phase_d import run_phase_d


class AEGShieldPhaseDTests(unittest.TestCase):
    def test_holdout_cases_are_frozen(self):
        result = run_phase_d()
        self.assertEqual(result["checks_total"], 5)
        self.assertEqual(
            [check["scenario"] for check in result["checks"]],
            [
                "future_timestamp",
                "correlation_id_evasion",
                "replay_with_new_ids",
                "trusted_producer_compromise",
                "missing_counterevidence",
            ],
        )


if __name__ == "__main__":
    unittest.main()
