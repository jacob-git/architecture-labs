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

## Falsifiable Phase A hypothesis

With the committed scenarios and fixed parameters:

1. 10,000 repetitions from one application and one causal path remain low-confidence under SHIELD even though a raw event threshold escalates them.
2. 50 observations distributed across applications, instances, regions, clusters, gateways, and paths reach high SHIELD confidence even though the raw event threshold does not fire.
3. 5,000 failures from many applications sharing one gateway and path are discounted below the genuinely independent 50-observation case.

If any of those relationships fail, Phase A fails.

## Scenarios

| Scenario | Events | Apps | Regions | Gateways | Paths | Expected SHIELD |
|---|---:|---:|---:|---:|---:|---|
| `correlated_retry_storm` | 10,000 | 1 | 1 | 1 | 1 | Low |
| `independent_corroboration` | 50 | 10 | 3 | 4 | 4 | High |
| `hidden_shared_gateway` | 5,000 | 50 | 1 | 1 | 1 | Medium, below independent corroboration |

The third case is deliberately adversarial to a simple `count(distinct reporters)` approach: it looks diverse at the application layer while retaining a shared causal bottleneck.

## Candidate SHIELD score

Phase A needs an executable scoring function, but SHIELD does **not** claim this function as canonical. It is a lab instrument that makes the architectural principle falsifiable.

The runner:

1. caps application-level source support so repeated events cannot grow evidence without bound;
2. makes observation volume saturate quickly;
3. measures topology diversity across regions, clusters, gateways, and paths;
4. applies an additional gateway/path bottleneck penalty;
5. converts resulting effective evidence into a bounded confidence score from 0 to 1.

The exact constants are committed in `core.py`, included in every result artifact, and covered by a digest. Later phases should vary these parameters rather than silently tune them after seeing outcomes.

## Run on Raspberry Pi 5 or any Python 3.11+ machine

No API key, model, database, container, or third-party Python package is required.

```bash
git pull
python3 --version
python3 -m unittest discover -s tests
python3 -m labs.shield_001.phase_a
```

The runner writes both the full machine-readable result and a compact human-readable summary:

```text
labs/shield_001/results/phase-a-latest.json
labs/shield_001/results/phase-a-latest.summary.md
```

Both generated files are ignored by Git until they are reviewed for publication. The Markdown summary contains provenance, digests, scenario results, claim checks, totals, and the interpretation boundary so it can be shared without pasting the full JSON.

For different output paths:

```bash
python3 -m labs.shield_001.phase_a \
  --output labs/shield_001/results/phase-a-rpi5.json \
  --summary-output labs/shield_001/results/phase-a-rpi5.summary.md
```

If `--summary-output` is omitted, the summary name is derived automatically from the JSON output path.

## What the result records

Each run stores:

- runner, scenario, and scoring versions;
- repository commit and dirty state;
- scenario and scoring digests;
- Python and platform information;
- all fixed scoring parameters;
- counts for applications, instances, hosts, clusters, regions, gateways, paths, and sessions;
- raw-threshold, distinct-reporter, and SHIELD decisions;
- SHIELD effective evidence, topology diversity, concentration, and confidence;
- explicit scenario and cross-scenario claim checks;
- limitations.

No chain-of-thought or private data is collected.

## Publication rule

Do not describe SHIELD Lab #001 as validated merely because the deterministic runner passes. Phase A proves only that the proposed experimental scoring function behaves as specified on the committed synthetic scenarios.

Before publishing a stronger claim, add sensitivity analysis, noisy and partially correlated topologies, failure/no-failure ground truth, precision/recall measurement, temporal evidence decay, and eventually replay against openly available or consented operational traces.

See [METHODOLOGY.md](METHODOLOGY.md) for the experiment design and [results/README.md](results/README.md) for the result review workflow.
