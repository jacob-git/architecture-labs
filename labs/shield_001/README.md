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

The third case is deliberately adversarial to a simple `count(distinct reporters)` approach: it looks diverse at the application layer while retaining a shared causal bottleneck.

Phase A is a deterministic regression baseline. It does not establish real-world effectiveness.

## Phase B — adversarial sensitivity and partial correlation

Phase B stops demonstrating hand-picked behavior and tries to break the v1 score.

It evaluates a deterministic matrix across:

- event volume: 10, 25, 50, 100, 500, and 2,000;
- application reporters: 1, 5, 10, and 50;
- regions: 1, 2, and 3;
- clusters, gateways, and paths: 1, 2, and 4 each;
- gateway and path concentration: 25%, 50%, 75%, 90%, and 99%.

It then checks four predeclared properties:

1. increasing topology cardinality must not reduce confidence;
2. repetition after the saturation region must add little confidence;
3. increasing concentration while preserving the same topology cardinality must materially reduce confidence;
4. a high-volume, 99%-concentrated topology must not outrank the balanced independent reference case.

The measured v1 Phase B result exposed a concrete weakness: cardinality alone could not distinguish balanced four-way evidence from 99%-concentrated four-way evidence. V1 therefore remains frozen as the version that produced that negative result.

## Evidence score v2 — distribution-aware revision

`shield-evidence-score-v2` is the first evidence-driven revision. It preserves v1's saturation, confidence mapping, targets, and Phase A/Phase B criteria, but replaces raw source cardinality with an inverse-Simpson effective source count.

That means these two distributions are no longer treated as equivalent:

```text
25%, 25%, 25%, 25%  → effective count ≈ 4
99%, 0.33%, 0.33%, 0.34% → effective count ≈ 1
```

The v2 validation runner executes both versions against the same committed evidence:

```text
v1 → Phase A must still PASS; frozen Phase B should reproduce its known FAIL
v2 → Phase A must still PASS; frozen Phase B must PASS without weakening criteria
```

The v2 scorer is in `scoring_v2.py`. V1 remains unchanged in `core.py`.

## Run on any Python 3.11+ machine

No API key, model, database, container, or third-party Python package is required.

```bash
git pull
python3 --version
python3 -m unittest discover -s tests
python3 -m labs.shield_001.phase_a
python3 -m labs.shield_001.phase_b
python3 -m labs.shield_001.v2_validation
```

Phase A writes:

```text
labs/shield_001/results/phase-a-latest.json
labs/shield_001/results/phase-a-latest.summary.md
```

Phase B writes:

```text
labs/shield_001/results/phase-b-latest.json
labs/shield_001/results/phase-b-latest.summary.md
```

V2 validation writes:

```text
labs/shield_001/results/v2-validation-latest.json
labs/shield_001/results/v2-validation-latest.summary.md
```

Generated JSON and summary files are ignored by Git until reviewed. Each summary includes provenance, digests, measurements, claim checks, and the interpretation boundary.

## Evidence rules

Each result records the runner/scenario or sweep/scoring versions, repository commit and dirty state, configuration digests, Python/platform information, measurements, explicit pass/fail checks, and limitations.

Do not describe SHIELD as validated merely because a deterministic phase passes. V2 was designed in response to a known synthetic counterexample, so passing the frozen regression suite demonstrates repair of that identified weakness, not production or causal validity.

Preserve negative results, revise candidate scores under new versions when evidence requires it, and continue toward noisy ground truth, temporal evidence, and real/open trace replay.

See [METHODOLOGY.md](METHODOLOGY.md) for experiment design and [results/README.md](results/README.md) for the publication workflow.
