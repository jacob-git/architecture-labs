from __future__ import annotations

import json
from pathlib import Path

from labs.adp_001.b2_evaluator import evaluate


def main() -> None:
    root = Path(__file__).resolve().parent
    reference = evaluate(root / "b2_reference_solution.py", mode="b2-reference")
    baseline = evaluate(root / "b2_baseline.py", mode="b2-unmodified-baseline")
    reference_passes = reference.passed == reference.total
    baseline_is_rejected = baseline.passed < baseline.total
    result = {
        "lab": "ADP-001",
        "phase": "B2 validation — constraint-dense cache harness",
        "model_calls": 0,
        "reference": reference.to_dict(),
        "baseline": baseline.to_dict(),
        "reference_solution_passes": reference_passes,
        "unmodified_baseline_is_rejected": baseline_is_rejected,
        "pass": reference_passes and baseline_is_rejected,
    }
    result_path = root / "results" / "phase-b2-validation-result.json"
    result_path.parent.mkdir(exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
