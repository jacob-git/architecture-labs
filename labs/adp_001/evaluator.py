from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class EvaluationResult:
    mode: str
    checks: tuple[CheckResult, ...]
    human_interventions: int = 0
    model_interactions: int = 0
    repair_attempts: int = 0

    @property
    def passed(self) -> int:
        return sum(check.passed for check in self.checks)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total else 0.0

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["passed"] = self.passed
        data["total"] = self.total
        data["score"] = round(self.score, 4)
        return data


def _run_pytest(path: Path) -> CheckResult:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (proc.stdout + proc.stderr).strip()
    return CheckResult(path.name, proc.returncode == 0, output[-2000:])


def _third_party_dependency_check(candidate: Path) -> CheckResult:
    forbidden = {"fastapi", "flask", "redis", "limits", "ratelimit", "slowapi"}
    hits: set[str] = set()
    for file in candidate.rglob("*.py"):
        text = file.read_text(encoding="utf-8")
        for name in forbidden:
            if f"import {name}" in text or f"from {name}" in text:
                hits.add(name)
    passed = not hits
    detail = "standard-library-only" if passed else f"forbidden imports: {sorted(hits)}"
    return CheckResult("dependency_policy", passed, detail)


def evaluate(candidate: Path, mode: str = "phase-a") -> EvaluationResult:
    root = Path(__file__).resolve().parent
    checks = (
        _run_pytest(root / "tests_visible.py"),
        _run_pytest(root / "tests_hidden.py"),
        _third_party_dependency_check(candidate),
    )
    return EvaluationResult(mode=mode, checks=checks)


def main() -> None:
    candidate = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent
    mode = sys.argv[2] if len(sys.argv) > 2 else "phase-a"
    result = evaluate(candidate, mode)
    print(json.dumps(result.to_dict(), indent=2))
    raise SystemExit(0 if result.passed == result.total else 1)


if __name__ == "__main__":
    main()
