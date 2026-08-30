# SHIELD Lab #001 Methodology

## Claim under test

SHIELD proposes that repeated observations are not automatically independent evidence. Confidence should strengthen when matching evidence comes from genuinely diverse causal paths and should strengthen less when observations share a hidden dependency or topology bottleneck.

This lab tests evidence weighting only. It does not test remediation authority or self-healing actions.

## Candidate score under test

The candidate `shield-evidence-score-v1` separates four ideas:

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

Confidence tiers are fixed before execution:

```text
low     < 0.35
medium  0.35 to < 0.75
high    >= 0.75
```

This equation is an experimental instrument, not a normative SHIELD requirement. Material revisions receive a new scoring version rather than silently rewriting v1 after observing failures.

## Phase A — fixed-scenario validation

### Correlated retry storm

10,000 identical failures originate from one application, instance, host, cluster, region, gateway, path, and session. The raw threshold should escalate. SHIELD should remain low because repetition adds almost no new independence.

### Independent corroboration

50 matching observations span 10 applications, 15 instances and hosts, six clusters, three regions, four gateways and paths, and 20 sessions. Raw volume remains below its threshold while SHIELD should reach high confidence.

### Hidden shared gateway

5,000 observations span 50 applications, 100 instances and hosts, and five clusters, but all observations share one region, gateway, and path. Both baseline thresholds escalate. SHIELD should discount the apparent source diversity and remain below the independent 50-observation scenario.

### Phase A pass criteria

1. independent corroboration confidence > correlated retry storm confidence;
2. hidden shared gateway confidence < independent corroboration confidence;
3. a scenario with more events can still have less SHIELD confidence when its evidence is more correlated.

Phase A is retained as a permanent deterministic regression baseline.

## Phase B — adversarial sensitivity and partial correlation

Phase B challenges `shield-evidence-score-v1` without changing its scoring constants.

### Matrix sweep

The runner evaluates all valid combinations of:

```text
events:    10, 25, 50, 100, 500, 2000
apps:      1, 5, 10, 50
regions:   1, 2, 3
clusters:  1, 2, 4
gateways:  1, 2, 4
paths:     1, 2, 4
```

Profiles where the number of observations cannot represent every requested unique dimension are excluded. The current sweep evaluates 1,782 valid profiles.

The matrix checks that increasing application or topology cardinality does not reduce confidence. It also records the largest adjacent score changes as a diagnostic for cliffs around caps and saturation regions.

### Partial-correlation sweep

Unique topology counts can hide concentration. To test that weakness directly, Phase B holds the following cardinality fixed:

```text
events = 500
apps = 20
regions = 3
clusters = 4
gateways = 4
paths = 4
```

It then concentrates gateway and path observations at:

```text
25%, 50%, 75%, 90%, 99%
```

Every level still contains all four gateways and all four paths. Only the distribution changes. This distinguishes cardinality from concentration.

Predeclared requirement: confidence must strictly decrease at each concentration step and the balanced-to-99%-concentrated drop must be at least `0.10`.

The 0.10 value is a Phase B stress criterion, not a universal SHIELD constant. Its purpose is to require material rather than numerically trivial sensitivity.

### Repetition saturation check

A maximally correlated one-app/one-region/one-cluster/one-gateway/one-path topology is evaluated at 10, 25, 50, 100, 500, 2,000, and 10,000 events.

Predeclared requirement: confidence gain from 100 to 10,000 events must be at most `0.01`.

### Adversarial ranking check

Two topologies are compared:

**Balanced reference**

```text
50 events
10 apps
3 regions
4 clusters
4 gateways
4 paths
25% maximum gateway/path concentration
```

**High-volume concentrated challenger**

```text
5,000 events
50 apps
3 regions
4 clusters
4 gateways
4 paths
99% gateway/path concentration
```

The second topology has the same unique topology cardinality but almost all observations share one gateway and path. Phase B requires that it not outrank the balanced independent reference.

### Phase B claim checks

Phase B passes only if all four properties hold:

1. **topology monotonicity** — increasing topology cardinality never reduces confidence;
2. **post-saturation volume bounded** — raw repetition adds little confidence after saturation;
3. **partial-correlation sensitivity** — concentration materially reduces confidence despite unchanged cardinality;
4. **adversarial ranking** — a high-volume concentrated topology does not outrank the balanced reference.

A Phase B failure is evidence. The runner intentionally exits with code `2` if any predeclared property fails. Unit tests validate the harness independently and should still pass.

## Reproducibility

Both phases use Python 3.11+ standard library only and no randomness. Results record the Git commit, dirty state, runner/scenario or sweep/scoring versions, configuration digests, Python version, platform, complete measurements, and limitations.

Generated JSON and Markdown summaries remain ignored until review. Formal publication requires a clean repository run or explicit classification of why provenance is unavailable.

## Threats to validity

- Synthetic topology is a proxy for real causal structure.
- Unique identifiers do not prove causal independence.
- Traffic concentration is evidence of possible correlation, not proof that two observations share a root cause.
- The Phase B material-drop threshold is an experimental stress criterion and requires future calibration.
- Neither phase has incident/non-incident ground truth, so precision, recall, false-positive rate, and false-negative rate are not yet measurable.
- Temporal ordering, evidence decay, contradictory evidence, source reliability, and adversarial telemetry are not modeled yet.

## Next phases

Evidence from Phase B should determine whether a new scoring version is needed before advancing.

- **Scoring v2 experiment** — incorporate concentration or richer causal/topology correlation without breaking Phase A invariants.
- **Temporal evidence** — introduce arrival order, decay, recovery, and recurrence.
- **Noisy ground truth** — inject incident and non-incident cases to measure calibration, precision, recall, and time-to-confidence.
- **Trace replay** — replay openly available or consented operational traces with topology metadata and compare against conventional detection.
