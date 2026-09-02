from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    requests_per_window: int
    window_seconds: int
    dependency_policy: str
    compatibility_required: bool


RATE_LIMIT_SPEC = FeatureSpec(
    name="per-client fixed-window rate limiting",
    requests_per_window=10,
    window_seconds=60,
    dependency_policy="standard-library-only",
    compatibility_required=True,
)

VISIBLE_REQUIREMENTS = (
    "Limit each client to 10 requests per 60-second window.",
    "Return HTTP 429 when a client exceeds its limit.",
    "Preserve existing endpoint behavior for allowed requests.",
    "Do not add third-party runtime dependencies.",
    "Add tests for the new behavior.",
)

HIDDEN_PROPERTIES = (
    "the 10th request succeeds and the 11th is rejected",
    "different client identities receive independent limits",
    "a new window restores capacity",
    "existing endpoint status codes and payloads remain compatible",
    "concurrent accounting does not allow the limit to be bypassed",
    "no third-party runtime dependency is introduced",
)
