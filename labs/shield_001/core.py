from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

RUNNER_VERSION = "shield-phase-a-runner-v1"
SCENARIO_VERSION = "shield-phase-a-scenarios-v1"
SCORING_VERSION = "shield-evidence-score-v1"
FAILURE_FINGERPRINT = "dependency-x-timeout"

RAW_EVENT_THRESHOLD = 100
DISTINCT_APP_THRESHOLD = 5
SHIELD_HIGH_CONFIDENCE = 0.75
SHIELD_MEDIUM_CONFIDENCE = 0.35

SHIELD_CONFIG = {
    "max_source_units": 12,
    "saturation_events": 25,
    "confidence_scale": 4.0,
    "diversity_targets": {
        "regions": 3,
        "clusters": 4,
        "gateways": 4,
        "paths": 4,
    },
    "confidence_tiers": {
        "low_below": SHIELD_MEDIUM_CONFIDENCE,
        "medium_below": SHIELD_HIGH_CONFIDENCE,
        "high_at_or_above": SHIELD_HIGH_CONFIDENCE,
    },
}

SCENARIO_SPECS = [
    {
        "id": "correlated_retry_storm",
        "title": "10,000 correlated repetitions from one causal path",
        "event_count": 10_000,
        "dimensions": {
            "apps": 1,
            "instances": 1,
            "hosts": 1,
            "clusters": 1,
            "regions": 1,
            "gateways": 1,
            "paths": 1,
            "sessions": 1,
        },
        "expected": {"raw": True, "distinct": False, "shield_tier": "low"},
    },
    {
        "id": "independent_corroboration",
        "title": "50 observations distributed across independent sources and paths",
        "event_count": 50,
        "dimensions": {
            "apps": 10,
            "instances": 15,
            "hosts": 15,
            "clusters": 6,
            "regions": 3,
            "gateways": 4,
            "paths": 4,
            "sessions": 20,
        },
        "expected": {"raw": False, "distinct": True, "shield_tier": "high"},
    },
    {
        "id": "hidden_shared_gateway",
        "title": "5,000 failures across many apps but one shared gateway and path",
        "event_count": 5_000,
        "dimensions": {
            "apps": 50,
            "instances": 100,
            "hosts": 100,
            "clusters": 5,
            "regions": 1,
            "gateways": 1,
            "paths": 1,
            "sessions": 50,
        },
        "expected": {"raw": True, "distinct": True, "shield_tier": "medium"},
    },
]


@dataclass(frozen=True)
class Observation:
    app: str
    instance: str
    host: str
    cluster: str
    region: str
    gateway: str
    path: str
    session: str
    fingerprint: str = FAILURE_FINGERPRINT


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    expected: dict[str, object]
    observations: tuple[Observation, ...]


def _value(prefix: str, index: int, count: int) -> str:
    return f"{prefix}-{index % count + 1}"


def build_scenario(spec: dict[str, object]) -> Scenario:
    dimensions = spec["dimensions"]
    assert isinstance(dimensions, dict)
    event_count = int(spec["event_count"])

    observations = tuple(
        Observation(
            app=_value("app", i, int(dimensions["apps"])),
            instance=_value("instance", i, int(dimensions["instances"])),
            host=_value("host", i, int(dimensions["hosts"])),
            cluster=_value("cluster", i, int(dimensions["clusters"])),
            region=_value("region", i, int(dimensions["regions"])),
            gateway=_value("gateway", i, int(dimensions["gateways"])),
            path=_value("path", i, int(dimensions["paths"])),
            session=_value("session", i, int(dimensions["sessions"])),
        )
        for i in range(event_count)
    )
    return Scenario(
        id=str(spec["id"]),
        title=str(spec["title"]),
        expected=dict(spec["expected"]),
        observations=observations,
    )


def build_scenarios() -> list[Scenario]:
    return [build_scenario(spec) for spec in SCENARIO_SPECS]


def unique_counts(observations: Iterable[Observation]) -> dict[str, int]:
    observations = tuple(observations)
    return {
        "events": len(observations),
        "apps": len({o.app for o in observations}),
        "instances": len({o.instance for o in observations}),
        "hosts": len({o.host for o in observations}),
        "clusters": len({o.cluster for o in observations}),
        "regions": len({o.region for o in observations}),
        "gateways": len({o.gateway for o in observations}),
        "paths": len({o.path for o in observations}),
        "sessions": len({o.session for o in observations}),
    }


def max_concentration(observations: Iterable[Observation], attribute: str) -> float:
    observations = tuple(observations)
    if not observations:
        return 0.0
    counts = Counter(getattr(o, attribute) for o in observations)
    return max(counts.values()) / len(observations)


def raw_threshold_detector(observations: Iterable[Observation]) -> dict[str, object]:
    observations = tuple(observations)
    count = len(observations)
    return {
        "detector": "raw-event-threshold-v1",
        "events": count,
        "threshold": RAW_EVENT_THRESHOLD,
        "escalated": count >= RAW_EVENT_THRESHOLD,
    }


def distinct_reporter_detector(observations: Iterable[Observation]) -> dict[str, object]:
    observations = tuple(observations)
    apps = len({o.app for o in observations})
    return {
        "detector": "distinct-app-threshold-v1",
        "distinctApps": apps,
        "threshold": DISTINCT_APP_THRESHOLD,
        "escalated": apps >= DISTINCT_APP_THRESHOLD,
    }


def _normalized_diversity(count: int, target: int) -> float:
    if target <= 0:
        raise ValueError("target must be positive")
    return min(count / target, 1.0)


def confidence_tier(confidence: float) -> str:
    if confidence >= SHIELD_HIGH_CONFIDENCE:
        return "high"
    if confidence >= SHIELD_MEDIUM_CONFIDENCE:
        return "medium"
    return "low"


def shield_detector(observations: Iterable[Observation]) -> dict[str, object]:
    """Candidate SHIELD scoring function for this lab, not a canonical formula.

    Repetition saturates quickly. Independent application sources contribute bounded
    support. Topology diversity across regions, clusters, gateways, and paths then
    adjusts how much of that support should count as genuinely independent evidence.
    A shared gateway/path acts as a bottleneck penalty.
    """

    observations = tuple(observations)
    counts = unique_counts(observations)
    if counts["events"] == 0:
        return {
            "detector": SCORING_VERSION,
            "confidence": 0.0,
            "tier": "low",
            "effectiveEvidence": 0.0,
            "sourceSupport": 0.0,
            "observationStrength": 0.0,
            "independenceFactor": 0.0,
            "topologyDiversity": {},
            "concentration": {},
        }

    targets = SHIELD_CONFIG["diversity_targets"]
    topology_diversity = {
        name: _normalized_diversity(counts[name], int(targets[name]))
        for name in ("regions", "clusters", "gateways", "paths")
    }

    geometric_diversity = math.prod(topology_diversity.values()) ** (1 / len(topology_diversity))
    bottleneck_penalty = math.sqrt(min(topology_diversity["gateways"], topology_diversity["paths"]))
    independence_factor = geometric_diversity * bottleneck_penalty

    source_support = min(counts["apps"], int(SHIELD_CONFIG["max_source_units"]))
    observation_strength = 1 - math.exp(-counts["events"] / float(SHIELD_CONFIG["saturation_events"]))
    effective_evidence = source_support * independence_factor * observation_strength
    confidence = 1 - math.exp(-effective_evidence / float(SHIELD_CONFIG["confidence_scale"]))

    concentration = {
        name: round(max_concentration(observations, name[:-1] if name.endswith("s") else name), 6)
        for name in ("regions", "clusters", "gateways", "paths")
    }

    return {
        "detector": SCORING_VERSION,
        "confidence": round(confidence, 6),
        "tier": confidence_tier(confidence),
        "effectiveEvidence": round(effective_evidence, 6),
        "sourceSupport": source_support,
        "observationStrength": round(observation_strength, 6),
        "independenceFactor": round(independence_factor, 6),
        "topologyDiversity": {k: round(v, 6) for k, v in topology_diversity.items()},
        "concentration": concentration,
    }


def evaluate_scenario(scenario: Scenario) -> dict[str, object]:
    raw = raw_threshold_detector(scenario.observations)
    distinct = distinct_reporter_detector(scenario.observations)
    shield = shield_detector(scenario.observations)
    counts = unique_counts(scenario.observations)

    checks = {
        "raw": raw["escalated"] is scenario.expected["raw"],
        "distinct": distinct["escalated"] is scenario.expected["distinct"],
        "shieldTier": shield["tier"] == scenario.expected["shield_tier"],
    }
    return {
        "scenarioId": scenario.id,
        "title": scenario.title,
        "failureFingerprint": FAILURE_FINGERPRINT,
        "counts": counts,
        "expected": scenario.expected,
        "rawThreshold": raw,
        "distinctReporter": distinct,
        "shield": shield,
        "checks": checks,
        "passed": all(checks.values()),
    }


def stable_digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def scenario_digest() -> str:
    return stable_digest(SCENARIO_SPECS)


def scoring_digest() -> str:
    return stable_digest(SHIELD_CONFIG)
