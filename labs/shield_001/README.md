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

Phase D was created only after temporal v2 was frozen. Its seven holdout checks test mixed fingerprints, stale diversity, time translation, delayed replay, repeated recovery, future-data isolation, and recurrence reset.

Temporal v2 passes 5/7 Phase D checks. The two new counterexamples are preserved in `phase_d.py` and documented in [`PHASE_D.md`](PHASE_D.md):

1. unrelated fingerprints can mutually reinforce into a high-confidence result;
2. stale evidence on different active topology units can escalate a fresh medium-confidence episode.

Phase D must remain frozen.

### Temporal evidence v3

`shield-temporal-evidence-v3` is a separate repair created after the Phase D failures.

Its changes are narrow:

- score each failure fingerprint as an independent temporal evidence partition and expose all partition scores;
- use the strongest partition as the overall confidence instead of pooling unrelated fingerprints;
- weight the freshness factor by each active unit's current episode volume, so high-volume stale units receive proportionate temporal discount.

Temporal v2 remains unchanged. Phase C, C2, and D remain unchanged.

The temporal-v3 validation runner accepts v3 only if the measured v2 baseline is reproduced, Phase C and C2 stay passing, Phase D reproduces the v2 5/7 holdout failure, and v3 passes all three frozen suites.

See [`TEMPORAL_V3.md`](TEMPORAL_V3.md).

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
```

Each runner also writes a `.summary.md` beside its JSON result. Generated outputs are ignored by Git until reviewed.

## Evidence rules

A passing deterministic phase is scoped evidence only. Preserve negative results, version material changes, and distinguish regression repair from independent holdout or real-world validation.

Phase D was an independent post-v2 synthetic holdout and therefore provides stronger evidence than the v2 repair regression. Temporal v3 was designed after observing Phase D, so passing Phase D under v3 would be regression-repair evidence, not a second independent holdout.

See [METHODOLOGY.md](METHODOLOGY.md) for the broader experiment design and [results/README.md](results/README.md) for publication rules.
