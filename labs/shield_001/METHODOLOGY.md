# SHIELD Lab #001 Methodology

## Claim under test

SHIELD proposes that repeated observations are not automatically independent evidence. Confidence should strengthen when matching evidence comes from genuinely diverse causal paths and should strengthen less when observations share a hidden dependency or topology bottleneck.

Phase A tests only that evidence-weighting claim. It does not test remediation authority or self-healing actions.

## Why three detectors

The experiment compares three deliberately different approaches against the exact same observation stream.

### 1. Raw event threshold

Escalates at 100 events. It represents volume-only alerting and intentionally ignores source identity and topology.

### 2. Distinct application threshold

Escalates at five applications. It improves on raw volume but treats applications as independent even when they share infrastructure.

### 3. Candidate SHIELD evidence score

The candidate score separates four ideas:

- **observation strength** — additional repeated events saturate quickly;
- **source support** — application reporters contribute bounded support;
- **topology diversity** — region, cluster, gateway, and path diversity increase independence;
- **bottleneck adjustment** — a shared gateway or path reduces the independence factor.

For a scenario with `E` events and `A` unique applications:

```text
source_support = min(A, 12)
observation_strength = 1 - exp(-E / 25)
```

For each topology dimension `d`:

```text
diversity_d = min(unique_d / target_d, 1)
```

Targets are three regions and four each for clusters, gateways, and paths. The geometric mean prevents one dimension from dominating the full score, while the explicit gateway/path bottleneck adjustment makes a shared routing dependency materially visible.

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

This equation is an experimental instrument, not a normative SHIELD requirement. A future result that depends on retuning it after seeing data should be recorded as a new scoring version.

## Phase A scenario design

### Correlated retry storm

10,000 identical failures originate from one application, instance, host, cluster, region, gateway, path, and session. The raw threshold should escalate. SHIELD should remain low because repetition adds almost no new independence.

### Independent corroboration

50 matching observations span 10 applications, 15 instances and hosts, six clusters, three regions, four gateways and paths, and 20 sessions. Raw volume remains below its threshold while SHIELD should reach high confidence.

### Hidden shared gateway

5,000 observations span 50 applications, 100 instances and hosts, and five clusters, but all observations share one region, gateway, and path. Both baseline thresholds escalate. SHIELD should discount the apparent source diversity and remain below the independent 50-observation scenario.

## Pass criteria

Phase A passes only when all scenario expectations and all three cross-scenario relationships pass:

1. independent corroboration confidence > correlated retry storm confidence;
2. hidden shared gateway confidence < independent corroboration confidence;
3. a scenario with more events can still have less SHIELD confidence when its evidence is more correlated.

The executable runner exits nonzero if these checks fail.

## Reproducibility

The runner records the current Git commit and dirty state, version constants, fixed configuration, SHA-256 digests of the scenario specification and scoring configuration, Python version, platform string, and complete aggregate outputs.

Phase A uses no randomness and no external dependencies. Two runs from the same clean commit and Python implementation should produce the same detector values; timestamps and platform metadata are expected to differ.

## Threats to validity

- Synthetic topology may not resemble real service dependency graphs.
- Unique identifiers are proxies for independence, not proof of causal independence.
- Fixed targets and thresholds may bias the observed confidence tiers.
- The shared-gateway case is intentionally obvious; real hidden correlations can be much harder to infer.
- No ground-truth incident classification is measured, so Phase A cannot report precision, recall, false-positive rate, or false-negative rate.
- No temporal ordering or evidence decay is modeled.
- No source reliability, contradictory evidence, adversarial telemetry, or missing topology is modeled.

These are inputs to later phases, not reasons to overstate Phase A.

## Next phases

- **Phase B — sensitivity and partial correlation:** sweep thresholds, diversity targets, event volumes, and mixed shared/independent paths.
- **Phase C — temporal evidence:** introduce arrival order, evidence decay, recovery, and recurrence.
- **Phase D — noisy ground truth:** inject failures and non-failures to measure calibration, precision, recall, and time-to-confidence.
- **Phase E — trace replay:** replay openly available or consented traces with topology metadata and compare against conventional alerting approaches.
