# SHIELD Lab #001 Methodology

## Claim under test

SHIELD proposes that repeated observations are not automatically independent evidence. Confidence should strengthen when matching evidence comes from genuinely diverse causal paths, should strengthen less when observations share a dependency bottleneck, and should weaken as evidence becomes stale or is superseded by recovery.

This lab tests evidence weighting and temporal confidence behavior only. It does not test remediation authority or self-healing actions.

## Candidate score v1

The original `shield-evidence-score-v1` separates four ideas:

- **observation strength** — additional repeated events saturate quickly;
- **source support** — application reporters contribute bounded support;
- **topology diversity** — region, cluster, gateway, and path cardinality increase independence;
- **bottleneck adjustment** — low gateway or path cardinality reduces the independence factor.

For a scenario with `E` events and `A` unique applications:

```text
source_support = min(A, 12)
observation_strength = 1 - exp(-E / 25)
```

For each topology dimension `d`:

```text
diversity_d = min(unique_d / target_d, 1)
```

Targets are three regions and four each for clusters, gateways, and paths.

```text
geometric_diversity = geometric_mean(region, cluster, gateway, path diversity)
bottleneck_penalty = sqrt(min(gateway_diversity, path_diversity))
independence_factor = geometric_diversity × bottleneck_penalty

effective_evidence = source_support × independence_factor × observation_strength
confidence = 1 - exp(-effective_evidence / 4)
```

Confidence tiers are fixed:

```text
low     < 0.35
medium  0.35 to < 0.75
high    >= 0.75
```

The equation is an experimental instrument, not a normative SHIELD requirement. Material revisions receive a new scoring version rather than silently rewriting earlier results.

## Phase A — fixed-scenario validation

Phase A retains three deterministic scenarios:

1. **correlated retry storm** — 10,000 repeated observations from one causal path;
2. **independent corroboration** — 50 observations distributed across applications and topology;
3. **hidden shared gateway** — 5,000 observations from many apps sharing one region, gateway, and path.

Phase A passes only when the fixed scenario expectations and cross-scenario ranking relationships hold. It is retained as a permanent regression baseline.

## Phase B — adversarial sensitivity and partial correlation

Phase B challenges v1 with the frozen 1,782-profile topology matrix:

```text
events:    10, 25, 50, 100, 500, 2000
apps:      1, 5, 10, 50
regions:   1, 2, 3
clusters:  1, 2, 4
gateways:  1, 2, 4
paths:     1, 2, 4
```

It also holds topology cardinality fixed while increasing gateway/path concentration through:

```text
25%, 50%, 75%, 90%, 99%
```

The frozen Phase B properties are:

1. topology cardinality must be monotonic;
2. post-saturation repetition must add little confidence;
3. partial correlation must materially reduce confidence;
4. a high-volume 99%-concentrated topology must not outrank the balanced reference.

V1 passed the first two and failed the last two. That negative result remains part of the record.

## Evidence score v2 — concentration-aware revision

V2 replaces raw cardinality with an inverse-Simpson effective source count.

For observation proportions `p_i` in one dimension:

```text
effective_count = 1 / Σ(p_i²)
```

Examples:

```text
25%, 25%, 25%, 25%               → effective_count = 4
99%, 0.33%, 0.33%, 0.34%         → effective_count ≈ 1
```

V2 calculates effective counts for applications, regions, clusters, gateways, and paths. The frozen Phase A and Phase B criteria are not weakened.

The clean reviewed v2 validation reproduced the v1 baseline, preserved all fixed Phase A outcomes, and passed all four unchanged Phase B checks. Because v2 was designed in response to the Phase B counterexample, that result is regression-repair evidence rather than an independent holdout validation.

## Phase C — temporal evidence, recovery, and recurrence

Phase C introduces `shield-temporal-evidence-v1` as a separate temporal layer on top of the frozen v2 structural model.

### Temporal evidence unit

The temporal layer groups evidence by:

```text
(app, region, cluster, gateway, path)
```

Repeated failure events can increase observation strength only until the existing v2 saturation behavior takes effect. The latest failure time for each active evidence unit determines its freshness.

### Decay

The Phase C experimental half-life is 30 minutes.

For evidence age `t`:

```text
freshness_weight = 0.5 ** (t / 30)
```

The half-life is a lab parameter selected to make temporal behavior observable in a compact deterministic experiment. It is not a production recommendation.

Weighted inverse-Simpson effective counts are calculated across active evidence units so newer topology evidence has more influence than stale topology evidence.

### Recovery semantics

A recovery signal for an evidence unit supersedes failure events for that same unit at or before the recovery time.

A failure arriving after recovery is treated as recurrence.

Recovery wins a timestamp tie because an active failure must be strictly newer than the latest recovery for the same evidence unit.

### Freshness after saturation

Phase C deliberately applies temporal freshness after volume saturation:

```text
effective_evidence =
    source_support
    × independence_factor
    × saturated_observation_strength
    × freshness_factor
```

This prevents historical event volume from defeating decay. A 5,000-event old incident should not remain high-confidence simply because it began with more observations than a smaller incident.

### Frozen Phase C scenarios

The Phase C scenario specification is committed and covered by a digest before result publication.

#### 1. Fresh independent accumulation

Twelve balanced evidence units are introduced in four batches at minutes:

```text
0, 5, 10, 15
```

Each batch introduces three new evidence units, each with five failure events.

Required behavior:

- confidence strictly increases at every step;
- the final state reaches the high tier.

#### 2. Passive decay

Sixty balanced failure events are observed at minute 0 and then no new evidence arrives.

Confidence is evaluated at:

```text
0, 30, 60, 90, 120 minutes
```

Required behavior:

- confidence strictly decreases at every evaluation;
- confidence is below high by minute 60;
- confidence is low by minute 120.

#### 3. Partial recovery

Six of the twelve balanced evidence units recover at minute 30.

Required behavior:

- confidence with recovery is at least `0.20` lower than the same timeline without recovery.

The `0.20` value is a Phase C stress criterion, not a universal SHIELD threshold.

#### 4. Full recovery and recurrence

All twelve evidence units recover at minute 45. Fresh balanced failures recur at minute 90.

Required behavior:

- after recovery, confidence is low;
- at minute 89, future recurrence evidence has no effect;
- at minute 90, fresh recurrence rebuilds confidence to high.

#### 5. Stale-volume guard

A balanced 5,000-event incident occurs at minute 0 and receives no fresh evidence.

At minute 120, four half-lives later, the result must be low-confidence.

This check specifically guards against event volume overpowering temporal decay.

#### 6. Input-order invariance

The same failure/recovery event set is evaluated in forward and reversed input order.

Required behavior:

- the complete temporal detector output is identical.

### Phase C claim checks

The runner reports seven explicit checks:

1. `freshIndependentEvidenceAccumulates`
2. `passiveDecayReducesConfidence`
3. `recoverySuppressesPriorFailures`
4. `recurrenceRebuildsConfidence`
5. `futureEvidenceDoesNotLeakBackward`
6. `staleVolumeCannotOverrideDecay`
7. `inputOrderInvariant`

A failing check is a valid experimental result. The runner exits nonzero rather than silently retuning Phase C after observing a failure.

## Reproducibility

All current runners use Python 3.11+ standard library only and no randomness. Results record the Git commit, dirty state, runner/scenario/scoring or temporal versions, configuration digests, Python version, platform, complete measurements, and limitations.

Generated JSON and Markdown summaries remain ignored until review. Formal publication requires a clean repository run or explicit classification of why provenance is unavailable.

## Threats to validity

- Synthetic topology is a proxy for real causal structure.
- Effective source counts and traffic distribution do not prove causal independence.
- The 30-minute half-life is arbitrary experimental calibration.
- Recovery is represented as a discrete source/topology state transition; real systems can recover partially or ambiguously.
- Clock skew, delayed telemetry, out-of-order timestamps, contradictory recovery/failure signals, source reliability, and adversarial timestamp manipulation are not modeled.
- Phase C reuses v2 topology assumptions rather than validating them against real dependency graphs.
- Incident/non-incident ground truth is still absent, so precision, recall, false-positive rate, and false-negative rate are not measurable.
- No remediation authority or action safety is evaluated.

## Next phases

After Phase C, the strongest next research steps are:

- **temporal adversarial tests** — clock skew, delayed signals, contradictory recovery, bursty recurrence, and stale-source poisoning;
- **holdout topology tests** — dependency structures not represented in the v2 design set;
- **noisy ground truth** — inject incident and non-incident cases to measure calibration, precision, recall, and time-to-confidence;
- **remediation authority** — map confidence to reversible, blast-radius-aware action levels;
- **trace replay** — openly available or consented operational traces with topology and timing metadata.
