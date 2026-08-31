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

Phase A establishes the basic behavior of `shield-evidence-score-v1` with three committed scenarios: a 10,000-event correlated retry storm, 50-event independent corroboration, and a 5,000-event many-app/shared-gateway case. Phase A is a deterministic regression baseline, not real-world validation.

## Phase B — adversarial sensitivity and partial correlation

Phase B evaluates the frozen 1,782-profile topology matrix plus gateway/path concentration stress cases. V1 passed topology monotonicity and repetition saturation but failed concentration sensitivity and adversarial ranking.

The negative result remains frozen. `shield-evidence-score-v2` replaced raw topology cardinality with inverse-Simpson effective source counts and subsequently passed the unchanged Phase B suite while preserving Phase A. Reviewed v2 evidence is in [`results/`](results/).

## Phase C — temporal evidence, recovery, and recurrence

Phase C introduces `shield-temporal-evidence-v1` on top of the frozen v2 structural score. It uses a 30-minute experimental half-life, recovery supersession, recurrence, and post-saturation freshness.

Its seven frozen checks cover fresh accumulation, passive decay, partial recovery, recurrence, future-data isolation, stale-volume resistance, and input-order invariance. Temporal v1 passes Phase C.

## Phase C2 — adversarial temporal robustness

Phase C2 attacks temporal v1 without changing Phase C. It adds seven adversarial checks for:

1. cross-fingerprint recovery isolation;
2. mixed stale + fresh history;
3. delayed recovery arrival;
4. bursty single-unit recurrence;
5. future clock skew visibility;
6. same-timestamp failure/recovery contradiction;
7. contradictory input-order invariance.

Temporal v1 passes only 3/7 Phase C2 checks. The four counterexamples are preserved in `phase_c2.py` and documented in [`PHASE_C2.md`](PHASE_C2.md).

## Temporal evidence v2 — adversarial repair

`shield-temporal-evidence-v2` is a separate revision. It does not overwrite temporal v1 or alter the frozen Phase C/C2 criteria.

The revision is intentionally narrow:

- recovery identity includes the failure fingerprint;
- current observation strength is based on each evidence unit's latest failure episode rather than its entire surviving history;
- future-dated events remain excluded from confidence but are surfaced as diagnostics;
- same-timestamp failure/recovery ties still resolve to recovery for confidence, while the contradiction remains explicitly visible.

The validation runner executes temporal v1 and temporal v2 against the same committed Phase C and Phase C2 harnesses. Temporal v2 is accepted by this regression only if the v1 history is reproduced, all seven Phase C checks stay passing, and all seven unchanged Phase C2 checks pass.

See [`TEMPORAL_V2.md`](TEMPORAL_V2.md) for the design boundary and limitations.

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
```

Generated outputs include:

```text
labs/shield_001/results/phase-a-latest.json
labs/shield_001/results/phase-b-latest.json
labs/shield_001/results/v2-validation-latest.json
labs/shield_001/results/phase-c-latest.json
labs/shield_001/results/phase-c2-latest.json
labs/shield_001/results/temporal-v2-validation-latest.json
```

Each runner also writes a `.summary.md` beside its JSON result. Generated outputs are ignored by Git until reviewed.

## Evidence rules

A passing deterministic phase is scoped evidence only. Preserve negative results, version material changes, and distinguish regression repair from independent holdout or real-world validation.

Temporal v2 was designed after observing the Phase C2 failures. Even if it passes the frozen suites, that establishes repair of those known counterexamples rather than independent production validity.

See [METHODOLOGY.md](METHODOLOGY.md) for the broader experiment design and [results/README.md](results/README.md) for publication rules.
