from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType


def load_candidate() -> ModuleType:
    configured = os.environ.get("ADP_CANDIDATE_FILE")
    if configured:
        path = Path(configured).resolve()
    else:
        path = Path(__file__).resolve().parent / "reference_solution.py"

    module_name = f"adp_candidate_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load candidate: {path}")

    module = importlib.util.module_from_spec(spec)
    # Register before execution so Python runtime features such as dataclasses
    # can resolve the module through sys.modules on Python 3.14+.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def rate_limited_api_type():
    module = load_candidate()
    candidate = getattr(module, "RateLimitedApi", None)
    if candidate is None:
        raise AttributeError("candidate must expose RateLimitedApi")
    return candidate
