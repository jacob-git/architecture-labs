from __future__ import annotations

import json
from pathlib import Path

from labs.adp_001.b4_evaluator import evaluate


def main() -> int:
    root = Path(__file__).resolve().parent
    reference = evaluate(root / "b4_reference_solution.py", "b4-reference")
    baseline = evaluate(root / "b4_baseline.py", "b4-unmodified-baseline")
    result = {
        "lab": "ADP-001",
        "phase": "B4 validation — runtime feedback harness",
        "model_calls": 0,
        "reference": reference.to_dict(),
        "baseline": baseline.to_dict(),
        "reference_solution_passes": reference.passed == reference.total,
        "unmodified_baseline_is_rejected": baseline.passed < baseline.total,
    }
    result["pass"] = result["reference_solution_passes"] and result["unmodified_baseline_is_rejected"]
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
