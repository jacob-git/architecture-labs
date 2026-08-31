import unittest

from labs.aeg_shield_001.phase_f import run_phase_f


class AEGShieldPhaseFTests(unittest.TestCase):
    def test_phase_f_holdouts_are_frozen(self):
        result = run_phase_f()
        self.assertEqual(6, result["checks_total"])
        self.assertFalse(result["holdout_survived"])
        self.assertEqual(
            [
                "stolen_signing_key",
                "revoked_key_still_accepted",
                "conflicting_trusted_producers",
                "authenticated_causal_collision",
                "partial_recovery_erases_full_incident",
                "low_and_slow_evidence_flood",
            ],
            [check["scenario"] for check in result["checks"]],
        )


if __name__ == "__main__":
    unittest.main()
