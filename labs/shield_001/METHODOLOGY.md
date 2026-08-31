# SHIELD Lab #001 Methodology

## Claim under test

SHIELD proposes that repeated observations are not automatically independent evidence. Confidence should strengthen when matching evidence comes from genuinely diverse causal paths and should strengthen less when observations share a hidden dependency or topology bottleneck.

This lab tests evidence weighting only. It does not test remediation authority or self-healing actions.

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

Profiles where the number of observations cannot represent every requested unique dimension are excluded. The frozen sweep evaluates 1,782 valid profiles.

### Partial-correlation sweep

Phase B holds cardinality fixed at 500 events, 20 apps, three regions, and four clusters/gateways/paths, then concentrates gateway and path observations at 25%, 50%, 75%, 90%, and 99%.

Every level still contains all four gateways and all four paths. Only the distribution changes.

Predeclared requirement: confidence must strictly decrease at each concentration step and the balanced-to-99%-concentrated drop must be at least `0.10`.

### Repetition saturation check

A maximally correlated one-app/one-region/one-cluster/one-gateway/one-path topology is evaluated at 10, 25, 50, 100, 500, 2,000, and 10,000 events.

Predeclared requirement: confidence gain from 100 to 10,000 events must be at most `0.01`.

### Adversarial ranking check

The frozen comparison is:

**Balanced reference**

```text
50 events
10 apps
3 regions
4 clusters
4 gateways
4 paths
25% gateway/path concentration
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

The second topology has the same unique topology cardinality but almost all observations share one gateway and path. It must not outrank the balanced reference.

### Phase B v1 finding

V1 passed topology monotonicity and repetition saturation but failed partial-correlation sensitivity and adversarial ranking. The 25% through 99% concentration sweep remained flat at the same confidence because v1 used unique counts rather than distribution.

That negative result is preserved. The Phase B sweep, thresholds, and expected properties are frozen for the v2 regression test.

## Evidence score v2 — concentration-aware revision

V2 replaces raw cardinality with an inverse-Simpson effective source count while preserving v1's other constants and confidence mapping.

For a dimension with observation proportions `p_i`:

```text
effective_count = 1 / Σ(p_i²)
```

Examples:

```text
25%, 25%, 25%, 25%               → effective_count = 4
99%, 0.33%, 0.33%, 0.34%         → effective_count ≈ 1
```

V2 calculates effective counts for applications, regions, clusters, gateways, and paths. These effective counts replace raw unique counts in source support and topology diversity.

The intended change is narrow: make confidence sensitive to concentration without weakening saturation or the fixed Phase A behavior.

## V2 acceptance criteria

The `v2_validation` runner executes both scoring versions against the same committed evidence. V2 is accepted by this lab only if all of these hold:

1. **v1 baseline preserved** — Phase A still passes and frozen Phase B still reproduces the known v1 failure;
2. **Phase A preserved** — all three fixed scenarios pass under v2 without changing their expected tiers;
3. **Frozen Phase B passes** — all four Phase B properties pass under v2;
4. **Sweep identity preserved** — both versions evaluate the same 1,782 profiles and the same sweep digest.

No Phase B expectation or threshold is changed to make v2 pass.

Passing this regression does not independently validate v2. V2 was designed after observing the Phase B counterexample, so this stage measures whether the identified weakness was repaired without breaking prior invariants.

## Reproducibility

All current runners use Python 3.11+ standard library only and no randomness. Results record the Git commit, dirty state, runner/sweep/scoring versions, configuration digests, Python version, platform, complete measurements, and limitations.

Generated JSON and Markdown summaries remain ignored until review. Formal publication requires a clean repository run or explicit classification of why provenance is unavailable.

## Threats to validity

- Synthetic topology is a proxy for real causal structure.
- Effective source counts measure distribution concentration, not causal independence.
- Traffic concentration is evidence of possible correlation, not proof that observations share a root cause.
- The Phase B material-drop threshold is an experimental stress criterion and requires future calibration.
- V2 was developed in response to the Phase B failure, so passing Phase B is not an independent holdout test.
- Incident/non-incident ground truth is still absent, so precision, recall, false-positive rate, and false-negative rate are not yet measurable.
- Temporal ordering, evidence decay, contradictory evidence, source reliability, and adversarial telemetry are not modeled yet.

## Next phases

If v2 survives independent reproduction, the next tests should add evidence that was not used to design v2:

- **holdout topology tests** — new distributions and dependency structures not represented in Phase B;
- **temporal evidence** — arrival order, decay, recovery, and recurrence;
- **noisy ground truth** — incident and non-incident cases to measure calibration, precision, recall, and time-to-confidence;
- **trace replay** — openly available or consented operational traces with topology metadata.
