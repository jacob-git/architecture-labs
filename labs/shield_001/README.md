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

Phase C2 then attacked temporal v1 with seven new adversarial cases. Temporal v1 passed only 3/7. The four counterexamples remain frozen in `phase_c2.py` and are documented in [`PHASE_C2.md`](PHASE_C2.md).

### Temporal evidence v2

`shield-temporal-evidence-v2` is a separate repair. It adds fingerprint-aware recovery identity, current-episode observation strength, future-timestamp diagnostics, and explicit same-timestamp conflict diagnostics.

The temporal-v2 regression runner requires the temporal-v1 history to remain reproducible while v2 passes all unchanged Phase C and C2 checks. See [`TEMPORAL_V2.md`](TEMPORAL_V2.md).

## Phase D — post-v2 temporal holdout

Phase D is a new suite created after temporal v2 was frozen. It is not used to tune temporal v2.

Its seven holdout checks cover:

1. non-reinforcement across unrelated failure fingerprints;
2. stale evidence on different topology units amplifying fresh evidence;
3. time-translation invariance;
4. delayed pre-recovery telemetry replay;
5. repeated-recovery idempotence;
6. future-data isolation with visible diagnostics;
7. fresh recurrence after a recovered historical incident.

A Phase D failure is valid evidence. Temporal v2 must not be edited in place to make the holdout pass.

The deterministic dry run passes five checks and exposes two new counterexamples: unrelated fingerprints can combine into high confidence, and stale evidence on different active units can escalate fresh evidence. See [`PHASE_D.md`](PHASE_D.md).

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
```

Each runner also writes a `.summary.md` beside its JSON result. Generated outputs are ignored by Git until reviewed.

## Evidence rules

A passing deterministic phase is scoped evidence only. Preserve negative results, version material changes, and distinguish regression repair from independent holdout or real-world validation.

Phase D was created after temporal v2 was frozen, so it is stronger than another repair regression. It is still synthetic and not blinded or externally sourced.

See [METHODOLOGY.md](METHODOLOGY.md) for the broader experiment design and [results/README.md](results/README.md) for publication rules.
