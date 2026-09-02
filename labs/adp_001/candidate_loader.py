from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType


def load_candidate() -> ModuleType:
    configured = os.environ.get("ADP_CANDIDATE_FILE")
    if configured:
        path = Path(configured).resolve()
    else:
        path = Path(__file__).resolve().parent / "reference_solution.py"

    spec = importlib.util.spec_from_file_location("adp_candidate", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load candidate: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rate_limited_api_type():
    module = load_candidate()
    candidate = getattr(module, "RateLimitedApi", None)
    if candidate is None:
        raise AttributeError("candidate must expose RateLimitedApi")
    return candidate
