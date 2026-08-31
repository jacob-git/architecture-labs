import unittest

from labs.aeg_shield_001.core import (
    Decision,
    EvidenceMemory,
    Proposal,
    RuntimeAction,
    RuntimeObservation,
    run_learning_cycle,
)


class AEGShieldIntegrationLabTests(unittest.TestCase):
    def test_safe_change_stays_allowed(self):
        result = run_learning_cycle(
            Proposal("p1", "cache_ttl", 0.20, 0.01, 120),
            RuntimeObservation(0.01, 160),
        )
        self.assertEqual(result["before"].decision, Decision.ALLOW)
        self.assertEqual(result["runtime_action"], RuntimeAction.NONE)
        self.assertEqual(result["after"].decision, Decision.ALLOW)

    def test_runtime_failure_feeds_back_into_governance(self):
        result = run_learning_cycle(
            Proposal("p2", "routing_rule", 0.35, 0.02, 220),
            RuntimeObservation(0.18, 860),
        )
        self.assertEqual(result["before"].decision, Decision.ALLOW)
        self.assertEqual(result["runtime_action"], RuntimeAction.ROLLBACK)
        self.assertEqual(result["after"].decision, Decision.DENY)
        self.assertAlmostEqual(result["memory"]["routing_rule"], 0.45)

    def test_policy_violation_is_severe_runtime_evidence(self):
        result = run_learning_cycle(
            Proposal("p3", "tool_permission", 0.30, 0.01, 180),
            RuntimeObservation(0.01, 190, policy_violation=True),
        )
        self.assertEqual(result["runtime_action"], RuntimeAction.ROLLBACK)
        self.assertEqual(result["after"].decision, Decision.DENY)

    def test_existing_memory_can_block_before_execution(self):
        memory = EvidenceMemory({"routing_rule": 0.45})
        result = run_learning_cycle(
            Proposal("p4", "routing_rule", 0.35, 0.02, 220),
            RuntimeObservation(0.01, 160),
            memory=memory,
        )
        self.assertEqual(result["before"].decision, Decision.DENY)
        self.assertEqual(result["runtime_action"], RuntimeAction.NONE)


if __name__ == "__main__":
    unittest.main()
