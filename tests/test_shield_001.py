import unittest

from labs.shield_001.core import (
    SCENARIO_SPECS,
    build_scenario,
    build_scenarios,
    evaluate_scenario,
    scenario_digest,
    shield_detector,
)
from labs.shield_001.phase_a import build_report, render_summary_markdown


class ShieldLab001Tests(unittest.TestCase):
    def test_all_committed_scenarios_match_expected_behavior(self):
        results = [evaluate_scenario(s) for s in build_scenarios()]
        self.assertTrue(all(result["passed"] for result in results))

    def test_fewer_independent_observations_beat_large_correlated_storm(self):
        storm, independent, _ = [evaluate_scenario(s) for s in build_scenarios()]
        self.assertEqual(storm["counts"]["events"], 10_000)
        self.assertEqual(independent["counts"]["events"], 50)
        self.assertGreater(independent["shield"]["confidence"], storm["shield"]["confidence"])
        self.assertEqual(storm["shield"]["tier"], "low")
        self.assertEqual(independent["shield"]["tier"], "high")

    def test_hidden_shared_gateway_is_discounted(self):
        _, independent, hidden = [evaluate_scenario(s) for s in build_scenarios()]
        self.assertGreater(hidden["counts"]["events"], independent["counts"]["events"])
        self.assertGreater(hidden["counts"]["apps"], independent["counts"]["apps"])
        self.assertTrue(hidden["distinctReporter"]["escalated"])
        self.assertLess(hidden["shield"]["confidence"], independent["shield"]["confidence"])
        self.assertEqual(hidden["shield"]["tier"], "medium")

    def test_repetition_saturates_without_new_independence(self):
        base = dict(SCENARIO_SPECS[0])
        base["dimensions"] = dict(SCENARIO_SPECS[0]["dimensions"])
        base["expected"] = dict(SCENARIO_SPECS[0]["expected"])

        short = dict(base)
        short["event_count"] = 100
        long = dict(base)
        long["event_count"] = 10_000

        short_score = shield_detector(build_scenario(short).observations)["confidence"]
        long_score = shield_detector(build_scenario(long).observations)["confidence"]
        self.assertLess(long_score - short_score, 0.01)

    def test_scenario_digest_is_stable_sha256(self):
        digest = scenario_digest()
        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, scenario_digest())

    def test_summary_contains_provenance_and_scenario_results(self):
        report = build_report()
        summary = render_summary_markdown(report)
        self.assertIn("SHIELD Lab #001", summary)
        self.assertIn(report["repositoryCommit"], summary)
        self.assertIn(report["scenarioDigest"], summary)
        self.assertIn("correlated_retry_storm", summary)
        self.assertIn("independent_corroboration", summary)
        self.assertIn("hidden_shared_gateway", summary)
        self.assertIn("Overall: **PASS**", summary)


if __name__ == "__main__":
    unittest.main()
