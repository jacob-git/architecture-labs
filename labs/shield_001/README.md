# SHIELD Lab #001 — Independent Evidence Reinforcement

This reproducible Python lab tests SHIELD's central claim: a large number of correlated repetitions should not create the same confidence as a smaller set of genuinely independent observations.

```text
RAW BASELINE:       event volume → threshold
REPORTER BASELINE:  distinct applications → threshold
SHIELD CANDIDATE:   bounded source support × topology independence → collective confidence
```

The environment, identities, dependency, topology, and incidents are entirely fictional. No external service or production system is touched.

## Research question

Can a correlation-aware evidence model assign higher confidence to a small, diverse set of independent observations than to a much larger set of repeated or causally shared observations?

## Phase A — fixed scenarios

Phase A establishes the basic behavior of `shield-evidence-score-v1` with three committed scenarios:

| Scenario | Events | Apps | Regions | Gateways | Paths | Expected SHIELD |
|---|---:|---:|---:|---:|---:|---|
| `correlated_retry_storm` | 10,000 | 1 | 1 | 1 | 1 | Low |
| `independent_corroboration` | 50 | 10 | 3 | 4 | 4 | High |
| `hidden_shared_gateway` | 5,000 | 50 | 1 | 1 | 1 | Medium, below independent corroboration |

Phase A is a deterministic regression baseline. It does not establish real-world effectiveness.

## Phase B — adversarial sensitivity and partial correlation

Phase B evaluates 1,782 deterministic topology profiles and challenges four predeclared properties: topology monotonicity, repetition saturation, partial-correlation sensitivity, and adversarial ranking.

The measured v1 result exposed a concrete weakness: raw topology cardinality could not distinguish balanced four-way evidence from evidence that was 99% concentrated on one gateway and path. V1 remains frozen as the scoring version that produced that negative result.

## Evidence score v2 — distribution-aware revision

`shield-evidence-score-v2` replaces raw source cardinality with an inverse-Simpson effective source count while preserving the frozen Phase A and Phase B criteria.

```text
25%, 25%, 25%, 25%              → effective count ≈ 4
99%, 0.33%, 0.33%, 0.34%        → effective count ≈ 1
```

A clean validation reproduced the v1 baseline, preserved Phase A, and moved the unchanged Phase B suite from 2/4 checks under v1 to 4/4 under v2. The reviewed summary and findings are in [`results/`](results/).

This is regression-repair evidence, not independent production validation.

## Phase C — temporal evidence, recovery, and recurrence

Phase C adds a candidate temporal layer, `shield-temporal-evidence-v1`, on top of the frozen v2 distribution-aware model. It does not rewrite v2.

The temporal model uses a 30-minute experimental half-life and treats an evidence unit as:

```text
(app, region, cluster, gateway, path)
```

For an active evidence unit with age `t`:

```text
freshness = 0.5 ** (t / half_life)
```

Recovery supersedes prior failures for the same evidence unit. A later failure on that unit is treated as recurrence.

The key design rule is that freshness is applied **after event-volume saturation**:

```text
effective_evidence =
    source_support
    × topology_independence
    × saturated_observation_strength
    × freshness
```

That prevents a very large historical incident from remaining authoritative merely because its original event count was large.

Phase C predeclares seven checks:

1. fresh independent evidence accumulates from low to high confidence;
2. passive confidence decays with no new evidence;
3. partial recovery materially reduces confidence;
4. full recovery clears prior evidence and fresh recurrence rebuilds confidence;
5. future recurrence evidence does not affect an earlier evaluation time;
6. a stale 5,000-event balanced incident cannot override decay;
7. input ordering does not change the temporal result.

The 30-minute half-life and recovery semantics are lab parameters, not production recommendations.

## Run on any Python 3.11+ machine

No API key, model, database, container, or third-party Python package is required.

```bash
git pull
python3 --version
python3 -m unittest discover -s tests
python3 -m labs.shield_001.phase_a
python3 -m labs.shield_001.phase_b
python3 -m labs.shield_001.v2_validation
python3 -m labs.shield_001.phase_c
```

Generated outputs:

```text
labs/shield_001/results/phase-a-latest.json
labs/shield_001/results/phase-a-latest.summary.md
labs/shield_001/results/phase-b-latest.json
labs/shield_001/results/phase-b-latest.summary.md
labs/shield_001/results/v2-validation-latest.json
labs/shield_001/results/v2-validation-latest.summary.md
labs/shield_001/results/phase-c-latest.json
labs/shield_001/results/phase-c-latest.summary.md
```

Generated JSON and summary files are ignored by Git until reviewed. Each summary includes provenance, digests, measurements, claim checks, and the interpretation boundary.

## Evidence rules

Each result records the runner/scenario or sweep/scoring versions, repository commit and dirty state, configuration digests, Python/platform information, measurements, explicit pass/fail checks, and limitations.

Do not describe SHIELD as validated merely because a deterministic phase passes. Preserve negative results, version material scoring changes, and distinguish regression evidence from independent holdout or real-world evidence.

See [METHODOLOGY.md](METHODOLOGY.md) for experiment design and [results/README.md](results/README.md) for the publication workflow.
