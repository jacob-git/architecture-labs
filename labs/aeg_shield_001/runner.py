from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum

from .core import run_scenarios


def _jsonable(value):
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {k: _jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def main() -> None:
    results = [_jsonable(result) for result in run_scenarios()]
    summary = {
        "lab": "AEG x SHIELD Lab #001",
        "claim": "runtime incident evidence can change a later governance decision for the same change class",
        "scenarios": results,
        "learning_demonstrated": any(
            r["before"]["decision"] == "allow" and r["after"]["decision"] == "deny"
            for r in results
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
