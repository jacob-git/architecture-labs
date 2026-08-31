from __future__ import annotations

import math
from collections import Counter
from typing import Iterable

from .core import (
    Observation,
    SHIELD_HIGH_CONFIDENCE,
    SHIELD_MEDIUM_CONFIDENCE,
    confidence_tier,
    max_concentration,
    stable_digest,
    unique_counts,
)

SCORING_VERSION_V2 = "shield-evidence-score-v2"

SHIELD_CONFIG_V2 = {
    "distribution_measure": "inverse-simpson-effective-count",
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


def effective_source_count(observations: Iterable[Observation], attribute: str) -> float:
    """Return inverse-Simpson effective count for one evidence dimension.

    Four evenly represented values produce an effective count of four. If one
    value carries nearly all observations, the effective count approaches one
    even when several rare values remain present.
    """

    observations = tuple(observations)
    if not observations:
        return 0.0

    counts = Counter(getattr(observation, attribute) for observation in observations)
    total = len(observations)
    concentration = sum((count / total) ** 2 for count in counts.values())
    return 0.0 if concentration == 0 else 1.0 / concentration


def _normalized_effective_diversity(effective_count: float, target: int) -> float:
    if target <= 0:
        raise ValueError("target must be positive")
    return min(effective_count / target, 1.0)


def shield_detector_v2(observations: Iterable[Observation]) -> dict[str, object]:
    """Distribution-aware SHIELD candidate score.

    V2 preserves the v1 saturation and confidence mapping but replaces raw
    topology cardinality with effective source counts derived from evidence
    concentration. This is an experimental lab instrument, not a canonical
    SHIELD formula.
    """

    observations = tuple(observations)
    counts = unique_counts(observations)
    if counts["events"] == 0:
        return {
            "detector": SCORING_VERSION_V2,
            "confidence": 0.0,
            "tier": "low",
            "effectiveEvidence": 0.0,
            "sourceSupport": 0.0,
            "observationStrength": 0.0,
            "independenceFactor": 0.0,
            "effectiveCounts": {},
            "topologyDiversity": {},
            "concentration": {},
        }

    effective_counts = {
        name: effective_source_count(
            observations,
            name[:-1] if name.endswith("s") else name,
        )
        for name in ("apps", "regions", "clusters", "gateways", "paths")
    }

    targets = SHIELD_CONFIG_V2["diversity_targets"]
    topology_diversity = {
        name: _normalized_effective_diversity(
            effective_counts[name],
            int(targets[name]),
        )
        for name in ("regions", "clusters", "gateways", "paths")
    }

    geometric_diversity = math.prod(topology_diversity.values()) ** (
        1 / len(topology_diversity)
    )
    bottleneck_penalty = math.sqrt(
        min(topology_diversity["gateways"], topology_diversity["paths"])
    )
    independence_factor = geometric_diversity * bottleneck_penalty

    source_support = min(
        effective_counts["apps"],
        float(SHIELD_CONFIG_V2["max_source_units"]),
    )
    observation_strength = 1 - math.exp(
        -counts["events"] / float(SHIELD_CONFIG_V2["saturation_events"])
    )
    effective_evidence = source_support * independence_factor * observation_strength
    confidence = 1 - math.exp(
        -effective_evidence / float(SHIELD_CONFIG_V2["confidence_scale"])
    )

    concentration = {
        name: round(
            max_concentration(
                observations,
                name[:-1] if name.endswith("s") else name,
            ),
            6,
        )
        for name in ("apps", "regions", "clusters", "gateways", "paths")
    }

    return {
        "detector": SCORING_VERSION_V2,
        "confidence": round(confidence, 6),
        "tier": confidence_tier(confidence),
        "effectiveEvidence": round(effective_evidence, 6),
        "sourceSupport": round(source_support, 6),
        "observationStrength": round(observation_strength, 6),
        "independenceFactor": round(independence_factor, 6),
        "effectiveCounts": {
            key: round(value, 6) for key, value in effective_counts.items()
        },
        "topologyDiversity": {
            key: round(value, 6) for key, value in topology_diversity.items()
        },
        "concentration": concentration,
    }


def scoring_digest_v2() -> str:
    return stable_digest(SHIELD_CONFIG_V2)
