from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def load_candidate():
    raw = os.environ.get("ADP_B4_CANDIDATE_FILE")
    if not raw:
        raise RuntimeError("ADP_B4_CANDIDATE_FILE is required")
    path = Path(raw).resolve()
    name = f"adp_b4_candidate_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load candidate: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def publishing_api_type():
    candidate = getattr(load_candidate(), "PublishingApi", None)
    if candidate is None:
        raise AttributeError("candidate must expose PublishingApi")
    return candidate
