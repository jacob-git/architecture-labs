from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .core import Observation, confidence_tier, stable_digest
from .scoring_v2 import SCORING_VERSION_V2, SHIELD_CONFIG_V2, scoring_digest_v2

TEMPORAL_MODEL_VERSION = "shield-temporal-evidence-v1"

TEMPORAL_CONFIG = {
    "base_scoring_version": SCORING_VERSION_V2,
    "base_scoring_digest": scoring_digest_v2(),
    "half_life_minutes": 30.0,
    "evidence_unit": ["app", "region", "cluster", "gateway", "path"],
    "recovery_semantics": "recovery-supersedes-prior-failures-per-evidence-unit",
    "freshness_application": "post-volume-saturation",
    "max_source_units": SHIELD_CONFIG_V2["max_source_units"],
    "saturation_events": SHIELD_CONFIG_V2["saturation_events"],
    "confidence_scale": SHIELD_CONFIG_V2["confidence_scale"],
    "diversity_targets": SHIELD_CONFIG_V2["diversity_targets"],
    "confidence_tiers": SHIELD_CONFIG_V2["confidence_tiers"],
}


@dataclass(frozen=True)
class TemporalEvent:
    observation: Observation
    minute: float
    state: str

    def __post_init__(self) -> None:
        if self.minute < 0:
            raise ValueError("minute must be non-negative")
        if self.state not in {"failure", "recovery"}:
            raise ValueError("state must be 'failure' or 'recovery'")


def evidence_unit_key(observation: Observation) -> tuple[str, str, str, str, str]:
    return (
        observation.app,
        observation.region,
        observation.cluster,
        observation.gateway,
        observation.path,
    )


def _freshness_weight(age_minutes: float) -> float:
    if age_minutes < 0:
        raise ValueError("age_minutes must be non-negative")
    half_life = float(TEMPORAL_CONFIG["half_life_minutes"])
    return 0.5 ** (age_minutes / half_life)


def _active_state(
    events: Iterable[TemporalEvent],
    now_minute: float,
) -> tuple[dict[tuple[str, str, str, str, str], TemporalEvent], int]:
    if now_minute < 0:
        raise ValueError("now_minute must be non-negative")

    failures: dict[
        tuple[str, str, str, str, str],
        list[TemporalEvent],
    ] = defaultdict(list)
    latest_recovery: dict[tuple[str, str, str, str, str], float] = {}

    for event in events:
        if event.minute > now_minute:
            continue
        key = evidence_unit_key(event.observation)
        if event.state == "recovery":
            latest_recovery[key] = max(
                latest_recovery.get(key, float("-inf")),
                event.minute,
            )
        else:
            failures[key].append(event)

    active_units: dict[
        tuple[str, str, str, str, str],
        TemporalEvent,
    ] = {}
    active_failure_events = 0

    for key, unit_failures in failures.items():
        recovery_minute = latest_recovery.get(key, float("-inf"))
        surviving = [event for event in unit_failures if event.minute > recovery_minute]
        if not surviving:
            continue
        latest = max(surviving, key=lambda event: event.minute)
        active_units[key] = latest
        active_failure_events += len(surviving)

    return active_units, active_failure_events


def _weighted_effective_count(
    active_units: dict[tuple[str, str, str, str, str], TemporalEvent],
    attribute: str,
    now_minute: float,
) -> float:
    totals: dict[str, float] = defaultdict(float)
    total_weight = 0.0

    for event in active_units.values():
        weight = _freshness_weight(now_minute - event.minute)
        totals[str(getattr(event.observation, attribute))] += weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    concentration = sum(weight * weight for weight in totals.values())
    return 0.0 if concentration == 0 else (total_weight * total_weight) / concentration


def temporal_detector(
    events: Iterable[TemporalEvent],
    now_minute: float,
) -> dict[str, object]:
    events = tuple(events)
    active_units, active_failure_events = _active_state(events, now_minute)

    if not active_units:
        return {
            "detector": TEMPORAL_MODEL_VERSION,
            "baseScoringVersion": SCORING_VERSION_V2,
            "confidence": 0.0,
            "tier": "low",
            "effectiveEvidence": 0.0,
            "sourceSupport": 0.0,
            "observationStrength": 0.0,
            "freshnessFactor": 0.0,
            "independenceFactor": 0.0,
            "activeEvidenceUnits": 0,
            "activeFailureEvents": 0,
            "effectiveCounts": {},
            "topologyDiversity": {},
        }

    freshness_weights = [
        _freshness_weight(now_minute - event.minute)
        for event in active_units.values()
    ]
    freshness_factor = sum(freshness_weights) / len(freshness_weights)

    effective_counts = {
        name: _weighted_effective_count(
            active_units,
            name[:-1] if name.endswith("s") else name,
            now_minute,
        )
        for name in ("apps", "regions", "clusters", "gateways", "paths")
    }

    targets = TEMPORAL_CONFIG["diversity_targets"]
    topology_diversity = {
        name: min(effective_counts[name] / float(targets[name]), 1.0)
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
        float(TEMPORAL_CONFIG["max_source_units"]),
    )
    observation_strength = 1 - math.exp(
        -active_failure_events / float(TEMPORAL_CONFIG["saturation_events"])
    )

    # Freshness is deliberately applied after event-volume saturation. This
    # prevents a very large historical burst from remaining authoritative merely
    # because its original event count was large.
    effective_evidence = (
        source_support
        * independence_factor
        * observation_strength
        * freshness_factor
    )
    confidence = 1 - math.exp(
        -effective_evidence / float(TEMPORAL_CONFIG["confidence_scale"])
    )

    return {
        "detector": TEMPORAL_MODEL_VERSION,
        "baseScoringVersion": SCORING_VERSION_V2,
        "confidence": round(confidence, 6),
        "tier": confidence_tier(confidence),
        "effectiveEvidence": round(effective_evidence, 6),
        "sourceSupport": round(source_support, 6),
        "observationStrength": round(observation_strength, 6),
        "freshnessFactor": round(freshness_factor, 6),
        "independenceFactor": round(independence_factor, 6),
        "activeEvidenceUnits": len(active_units),
        "activeFailureEvents": active_failure_events,
        "effectiveCounts": {
            key: round(value, 6) for key, value in effective_counts.items()
        },
        "topologyDiversity": {
            key: round(value, 6) for key, value in topology_diversity.items()
        },
    }


def temporal_config_digest() -> str:
    return stable_digest(TEMPORAL_CONFIG)
