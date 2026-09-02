from __future__ import annotations

import json
from pathlib import Path

from labs.adp_001.evaluator import evaluate


def main() -> None:
    root = Path(__file__).resolve().parent
    reference = evaluate(root / "reference_solution.py", mode="reference")
    baseline = evaluate(root / "baseline.py", mode="unmodified-baseline")

    reference_passes = reference.passed == reference.total
    baseline_is_rejected = baseline.passed < baseline.total

    result = {
        "lab": "ADP-001",
        "phase": "A — deterministic harness validation",
        "feature": "per-client fixed-window API rate limiting",
        "model_calls": 0,
        "reference": reference.to_dict(),
        "baseline": baseline.to_dict(),
        "reference_solution_passes": reference_passes,
        "unmodified_baseline_is_rejected": baseline_is_rejected,
        "pass": reference_passes and baseline_is_rejected,
    }

    results_dir = root / "results"
    results_dir.mkdir(exist_ok=True)
    result_path = results_dir / "phase-a-result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
