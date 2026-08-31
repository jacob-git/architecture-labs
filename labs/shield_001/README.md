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

## Evidence history

### Phase A and Phase B

Phase A established the basic behavior of `shield-evidence-score-v1`. The frozen 1,782-profile Phase B suite then exposed v1 concentration blindness and an adversarial ranking inversion.

`shield-evidence-score-v2` introduced inverse-Simpson effective source counts and passed the unchanged Phase A and Phase B regression suites. Reviewed v2 evidence is in [`results/`](results/).

### Phase C and Phase C2

Phase C introduced `shield-temporal-evidence-v1` with a 30-minute experimental half-life, recovery supersession, recurrence, and post-saturation freshness. Temporal v1 passed all seven Phase C checks.

Phase C2 attacked temporal v1 with seven new adversarial cases. Temporal v1 passed only 3/7. The four counterexamples remain frozen in `phase_c2.py` and are documented in [`PHASE_C2.md`](PHASE_C2.md).

### Temporal evidence v2

`shield-temporal-evidence-v2` repaired the Phase C2 failures by adding fingerprint-aware recovery identity, current-episode observation strength, future-timestamp diagnostics, and explicit same-timestamp conflict diagnostics.

Temporal v2 preserves all seven Phase C checks and passes all seven Phase C2 checks. See [`TEMPORAL_V2.md`](TEMPORAL_V2.md).

### Phase D — post-v2 holdout

Phase D was created only after temporal v2 was frozen. Temporal v2 passes 5/7 Phase D checks. The two new counterexamples are preserved in `phase_d.py` and documented in [`PHASE_D.md`](PHASE_D.md):

1. unrelated fingerprints can mutually reinforce into a high-confidence result;
2. stale evidence on different active topology units can escalate a fresh medium-confidence episode.

Phase D remains frozen.

### Temporal evidence v3

`shield-temporal-evidence-v3` repairs those Phase D failures by partitioning confidence by fingerprint and weighting freshness by current episode volume.

The temporal-v3 validation runner requires the measured v2 baseline and Phase D failure to remain reproducible while v3 passes unchanged Phase C, C2, and D. See [`TEMPORAL_V3.md`](TEMPORAL_V3.md).

### Phase E — noisy ground truth and calibration

Phase E is the first labeled incident/non-incident corpus. Temporal v3 remains frozen.

The corpus contains 24 deterministic cases: 12 incident and 12 non-incident. At the existing SHIELD high-confidence boundary (`0.75`), Phase E measures precision, recall, false-positive rate, exploratory calibration diagnostics, and time to high confidence.

The deterministic dry run gives `9 TP / 0 FP / 12 TN / 3 FN`: precision `1.00`, recall `0.75`, and FPR `0.00`. The frozen recall requirement is `>= 0.80`, so Phase E is intentionally preserved as **FAIL 6/7**.

The three false negatives are real synthetic shared-cause incidents whose observations share a gateway, a path, or both. This demonstrates a key boundary: SHIELD confidence can remain conservative even when the underlying incident is real.

See [`PHASE_E.md`](PHASE_E.md).

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
python3 -m labs.shield_001.phase_c2
python3 -m labs.shield_001.temporal_v2_validation
python3 -m labs.shield_001.phase_d
python3 -m labs.shield_001.temporal_v3_validation
python3 -m labs.shield_001.phase_e
```

Generated outputs include:

```text
labs/shield_001/results/phase-a-latest.json
labs/shield_001/results/phase-b-latest.json
labs/shield_001/results/v2-validation-latest.json
labs/shield_001/results/phase-c-latest.json
labs/shield_001/results/phase-c2-latest.json
labs/shield_001/results/temporal-v2-validation-latest.json
labs/shield_001/results/phase-d-latest.json
labs/shield_001/results/temporal-v3-validation-latest.json
labs/shield_001/results/phase-e-latest.json
```

Each runner also writes a `.summary.md` beside its JSON result. Generated outputs are ignored by Git until reviewed.

## Evidence rules

A passing deterministic phase is scoped evidence only. Preserve negative results, version material changes, and distinguish regression repair from independent holdout or real-world validation.

Phase E is synthetic, balanced, and authored in the same repository. It is the first phase to measure labeled detector performance, but it is not an external or blinded validation. Do not optimize the high-confidence threshold against this corpus after seeing the labels.

See [METHODOLOGY.md](METHODOLOGY.md) for the broader experiment design and [results/README.md](results/README.md) for publication rules.
