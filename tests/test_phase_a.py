import json
import unittest
from pathlib import Path

from labs.aeg_001.phase_a import run_scenarios
from labs.aeg_001.scenarios_b import PHASE_B_SCENARIOS


class LabRegressionTests(unittest.TestCase):
    def test_phase_a_measured_baseline(self) -> None:
        path = Path(__file__).parents[1] / "labs" / "aeg_001" / "scenarios.json"
        result = run_scenarios(json.loads(path.read_text(encoding="utf-8")))
        summary = result["summary"]
        self.assertEqual(40, summary["scenarios"])
        self.assertEqual(40, summary["governedPasses"])
        self.assertEqual(35, summary["attackOrEdgeCasePasses"])
        self.assertEqual(32, summary["unsafeScenarioCount"])
        self.assertEqual(27, summary["baselineUnsafeExecuted"])
        self.assertEqual(0, summary["aegUnsafeExecuted"])

    def test_phase_b_corpus_is_fixed_at_120(self) -> None:
        self.assertEqual(120, len(PHASE_B_SCENARIOS))
        self.assertEqual(120, len({scenario["id"] for scenario in PHASE_B_SCENARIOS}))


if __name__ == "__main__":
    unittest.main()
