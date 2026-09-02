from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _pytest(path: Path) -> dict[str, object]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "path": path.name,
        "passed": proc.returncode == 0,
        "output": (proc.stdout + proc.stderr).strip(),
    }


def main() -> None:
    root = Path(__file__).resolve().parent
    visible = _pytest(root / "tests_visible.py")
    hidden = _pytest(root / "tests_hidden.py")

    result = {
        "lab": "ADP-001",
        "phase": "A — deterministic harness validation",
        "feature": "per-client fixed-window API rate limiting",
        "model_calls": 0,
        "visible_suite": visible,
        "hidden_suite": hidden,
        "reference_solution_passes": bool(visible["passed"] and hidden["passed"]),
        "pass": bool(visible["passed"] and hidden["passed"]),
    }

    results_dir = root / "results"
    results_dir.mkdir(exist_ok=True)
    result_path = results_dir / "phase-a-result.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
