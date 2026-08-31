from __future__ import annotations

import math
from collections import defaultdict
from typing import Iterable

from .core import Observation, confidence_tier, stable_digest
from .scoring_v2 import SCORING_VERSION_V2
from .temporal_v1 import TemporalEvent
from .temporal_v2 import (
    TEMPORAL_CONFIG_V2,
    TEMPORAL_MODEL_VERSION_V2,
    temporal_config_digest_v2,
)

TEMPORAL_MODEL_VERSION_V3 = "shield-temporal-evidence-v3"

TEMPORAL_CONFIG_V3 = {
    "base_temporal_model_version": TEMPORAL_MODEL_VERSION_V2,
    "base_temporal_config_digest": temporal_config_digest_v2(),
    "base_scoring_version": SCORING_VERSION_V2,
    "fingerprint_aggregation": "partition-and-select-max-confidence",
    "freshness_aggregation": "latest-episode-volume-weighted",
    "evidence_unit": list(TEMPORAL_CONFIG_V2["evidence_unit"]),
    "recovery_semantics": TEMPORAL_CONFIG_V2["recovery_semantics"],
    "observation_strength_semantics": TEMPORAL_CONFIG_V2["observation_strength_semantics"],
    "future_timestamp_semantics": TEMPORAL_CONFIG_V2["future_timestamp_semantics"],
    "timestamp_tie_semantics": TEMPORAL_CONFIG_V2["timestamp_tie_semantics"],
    "half_life_minutes": TEMPORAL_CONFIG_V2["half_life_minutes"],
    "freshness_application": TEMPORAL_CONFIG_V2["freshness_application"],
    "max_source_units": TEMPORAL_CONFIG_V2["max_source_units"],
    "saturation_events": TEMPORAL_CONFIG_V2["saturation_events"],
    "confidence_scale": TEMPORAL_CONFIG_V2["confidence_scale"],
    "diversity_targets": TEMPORAL_CONFIG_V2["diversity_targets"],
    "confidence_tiers": TEMPORAL_CONFIG_V2["confidence_tiers"],
}


def evidence_unit_key_v3(
    observation: Observation,
) -> tuple[str, str, str, str, str, str]:
    return (
        observation.fingerprint,
        observation.app,
        observation.region,
        observation.cluster,
        observation.gateway,
        observation.path,
    )


def _freshness_weight(age_minutes: float) -> float:
    if age_minutes < 0:
        raise ValueError("age_minutes must be non-negative")
    half_life = float(TEMPORAL_CONFIG_V3["half_life_minutes"])
    return 0.5 ** (age_minutes / half_life)


def _active_state(
    events: tuple[TemporalEvent, ...],
    now_minute: float,
) -> tuple[
    dict[tuple[str, str, str, str, str, str], tuple[TemporalEvent, int, int]],
    int,
    int,
]:
    grouped: dict[
        tuple[str, str, str, str, str, str],
        list[TemporalEvent],
    ] = defaultdict(list)

    for event in events:
        if event.minute <= now_minute:
            grouped[evidence_unit_key_v3(event.observation)].append(event)

    active_units: dict[
        tuple[str, str, str, str, str, str],
        tuple[TemporalEvent, int, int],
    ] = {}
    active_failure_events = 0
    active_episode_failure_events = 0

    for key, unit_events in grouped.items():
        recovery_minutes = [
            event.minute for event in unit_events if event.state == "recovery"
        ]
        latest_recovery = max(recovery_minutes) if recovery_minutes else float("-inf")
        surviving_failures = [
            event
            for event in unit_events
            if event.state == "failure" and event.minute > latest_recovery
        ]
        if not surviving_failures:
            continue

        latest_failure_minute = max(event.minute for event in surviving_failures)
        latest_failure = max(surviving_failures, key=lambda event: event.minute)
        episode_count = sum(
            event.minute == latest_failure_minute for event in surviving_failures
        )
        active_units[key] = (
            latest_failure,
            len(surviving_failures),
            episode_count,
        )
        active_failure_events += len(surviving_failures)
        active_episode_failure_events += episode_count

    return active_units, active_failure_events, active_episode_failure_events


def _weighted_effective_count(
    active_units: dict[
        tuple[str, str, str, str, str, str],
        tuple[TemporalEvent, int, int],
    ],
    attribute: str,
    now_minute: float,
) -> float:
    totals: dict[str, float] = defaultdict(float)
    total_weight = 0.0

    for latest_failure, _, _ in active_units.values():
        weight = _freshness_weight(now_minute - latest_failure.minute)
        totals[str(getattr(latest_failure.observation, attribute))] += weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    concentration = sum(weight * weight for weight in totals.values())
    return 0.0 if concentration == 0 else (total_weight * total_weight) / concentration


def _global_diagnostics(
    events: tuple[TemporalEvent, ...],
    now_minute: float,
) -> dict[str, object]:
    future_events = [event for event in events if event.minute > now_minute]
    grouped_states: dict[
        tuple[tuple[str, str, str, str, str, str], float],
        set[str],
    ] = defaultdict(set)

    for event in events:
        if event.minute <= now_minute:
            grouped_states[
                (evidence_unit_key_v3(event.observation), event.minute)
            ].add(event.state)

    conflict_units = {
        key
        for (key, _), states in grouped_states.items()
        if len(states) > 1
    }
    max_future_skew = max(
        (event.minute - now_minute for event in future_events),
        default=0.0,
    )

    return {
        "futureEventCount": len(future_events),
        "maxFutureSkewMinutes": round(max_future_skew, 6),
        "timestampConflictUnits": len(conflict_units),
    }


def _empty_partition_result() -> dict[str, object]:
    return {
        "confidence": 0.0,
        "tier": "low",
        "effectiveEvidence": 0.0,
        "sourceSupport": 0.0,
        "observationStrength": 0.0,
        "freshnessFactor": 0.0,
        "independenceFactor": 0.0,
        "activeEvidenceUnits": 0,
        "activeFailureEvents": 0,
        "activeEpisodeFailureEvents": 0,
        "historicalFailureEventsExcludedFromStrength": 0,
        "effectiveCounts": {},
        "topologyDiversity": {},
    }


def _score_fingerprint_partition(
    events: tuple[TemporalEvent, ...],
    now_minute: float,
) -> dict[str, object]:
    (
        active_units,
        active_failure_events,
        active_episode_failure_events,
    ) = _active_state(events, now_minute)

    if not active_units:
        return _empty_partition_result()

    weighted_episode_freshness = sum(
        _freshness_weight(now_minute - latest_failure.minute) * episode_count
        for latest_failure, _, episode_count in active_units.values()
    )
    freshness_factor = (
        weighted_episode_freshness / active_episode_failure_events
        if active_episode_failure_events
        else 0.0
    )

    effective_counts = {
        name: _weighted_effective_count(
            active_units,
            name[:-1] if name.endswith("s") else name,
            now_minute,
        )
        for name in ("apps", "regions", "clusters", "gateways", "paths")
    }

    targets = TEMPORAL_CONFIG_V3["diversity_targets"]
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
        float(TEMPORAL_CONFIG_V3["max_source_units"]),
    )
    observation_strength = 1 - math.exp(
        -active_episode_failure_events
        / float(TEMPORAL_CONFIG_V3["saturation_events"])
    )
    effective_evidence = (
        source_support
        * independence_factor
        * observation_strength
        * freshness_factor
    )
    confidence = 1 - math.exp(
        -effective_evidence / float(TEMPORAL_CONFIG_V3["confidence_scale"])
    )

    return {
        "confidence": round(confidence, 6),
        "tier": confidence_tier(confidence),
        "effectiveEvidence": round(effective_evidence, 6),
        "sourceSupport": round(source_support, 6),
        "observationStrength": round(observation_strength, 6),
        "freshnessFactor": round(freshness_factor, 6),
        "independenceFactor": round(independence_factor, 6),
        "activeEvidenceUnits": len(active_units),
        "activeFailureEvents": active_failure_events,
        "activeEpisodeFailureEvents": active_episode_failure_events,
        "historicalFailureEventsExcludedFromStrength": (
            active_failure_events - active_episode_failure_events
        ),
        "effectiveCounts": {
            key: round(value, 6) for key, value in effective_counts.items()
        },
        "topologyDiversity": {
            key: round(value, 6) for key, value in topology_diversity.items()
        },
    }


def temporal_detector_v3(
    events: Iterable[TemporalEvent],
    now_minute: float,
) -> dict[str, object]:
    if now_minute < 0:
        raise ValueError("now_minute must be non-negative")

    events = tuple(events)
    diagnostics = _global_diagnostics(events, now_minute)
    fingerprints = sorted({event.observation.fingerprint for event in events})

    partition_scores: dict[str, dict[str, object]] = {}
    for fingerprint in fingerprints:
        partition_events = tuple(
            event
            for event in events
            if event.observation.fingerprint == fingerprint
        )
        partition_scores[fingerprint] = _score_fingerprint_partition(
            partition_events,
            now_minute,
        )

    active_fingerprints = [
        fingerprint
        for fingerprint, score in partition_scores.items()
        if int(score["activeEvidenceUnits"]) > 0
    ]

    if active_fingerprints:
        selected_fingerprint = max(
            active_fingerprints,
            key=lambda fingerprint: (
                float(partition_scores[fingerprint]["confidence"]),
                fingerprint,
            ),
        )
        selected = dict(partition_scores[selected_fingerprint])
    else:
        selected_fingerprint = None
        selected = _empty_partition_result()

    fingerprint_scores = {
        fingerprint: {
            "confidence": score["confidence"],
            "tier": score["tier"],
            "activeEvidenceUnits": score["activeEvidenceUnits"],
            "activeEpisodeFailureEvents": score[
                "activeEpisodeFailureEvents"
            ],
            "freshnessFactor": score["freshnessFactor"],
        }
        for fingerprint, score in partition_scores.items()
    }

    return {
        "detector": TEMPORAL_MODEL_VERSION_V3,
        "baseTemporalModelVersion": TEMPORAL_MODEL_VERSION_V2,
        "baseScoringVersion": SCORING_VERSION_V2,
        **selected,
        **diagnostics,
        "fingerprintCount": len(fingerprints),
        "activeFingerprintCount": len(active_fingerprints),
        "selectedFingerprint": selected_fingerprint,
        "fingerprintScores": fingerprint_scores,
    }


def temporal_config_digest_v3() -> str:
    return stable_digest(TEMPORAL_CONFIG_V3)
