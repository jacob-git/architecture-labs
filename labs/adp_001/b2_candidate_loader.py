from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType


def load_candidate() -> ModuleType:
    configured = os.environ.get("ADP_B2_CANDIDATE_FILE")
    path = Path(configured).resolve() if configured else Path(__file__).resolve().parent / "b2_reference_solution.py"
    module_name = "adp_b2_candidate"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"unable to load candidate: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def cached_api_type():
    module = load_candidate()
    candidate = getattr(module, "CachedApi", None)
    if candidate is None:
        raise AttributeError("candidate must expose CachedApi")
    return candidate
