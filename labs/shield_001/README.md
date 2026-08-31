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

### Phase F — confidence, severity, and remediation authority

Phase F does not change temporal v3 or the Phase E labels. It introduces a separate candidate policy for turning evidence into bounded action authority.

The policy consumes temporal v3 confidence, severity/impact, reversibility, blast radius, and an explicit safety-gate result. Severity can increase urgency without manufacturing confidence. Medium confidence can never authorize `isolate` or `recover`, and a failed safety gate always caps authority at `observe`.

See [`PHASE_F.md`](PHASE_F.md).

### Phase F2 — adversarial authority-input trust

Phase F2 freezes the Phase F policy and attacks the trustworthiness of its policy inputs. Declared metadata is evaluated separately from trusted ground truth.

The seven checks cover spoofed severity, false reversibility, underestimated blast radius, stale impact, contradictory safety gates, unverified rollback, and an explicit safety-failure baseline.

The deterministic result is **1/7 PASS**. Phase F v1 fails closed only when `safetyPass=False` is explicitly supplied. In the other six scenarios, untrusted or stale metadata can cause authority to exceed the frozen maximum-safe-authority bound.

This establishes a new boundary: authority safety requires provenance, freshness, and verification of policy inputs, not just good confidence scoring and rule logic.

See [`PHASE_F2.md`](PHASE_F2.md).

### Remediation authority policy v2

`shield-remediation-authority-policy-v2` is a separate repair. Phase F and F2 remain frozen.

V2 introduces `shield-authority-evidence-envelope-v1`. Every authority-bearing input carries a source, trust status, verification status, and age. Safety carries the underlying required signals instead of a pre-collapsed boolean.

The fail-closed rules are:

- untrusted, stale, unverified, empty, or contradictory safety evidence caps authority at `observe`;
- untrusted, stale, or unverified severity, reversibility, or blast-radius evidence caps authority at `validate`;
- any `mitigate` or `isolate` authority that depends on reversibility requires independently verified rollback capability;
- temporal v3 confidence remains unchanged.

The authority-v2 validation runner must reproduce the policy-v1 history, including the Phase F2 `1/7` negative result, and then pass the unchanged Phase F and F2 suites under policy v2.

See [`AUTHORITY_V2.md`](AUTHORITY_V2.md).

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
python3 -m labs.shield_001.phase_f
python3 -m labs.shield_001.phase_f2
python3 -m labs.shield_001.authority_v2_validation
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
labs/shield_001/results/phase-f-latest.json
labs/shield_001/results/phase-f2-latest.json
labs/shield_001/results/authority-v2-validation-latest.json
```

Each runner also writes a `.summary.md` beside its JSON result. Generated outputs are ignored by Git until reviewed.

## Evidence rules

A passing deterministic phase is scoped evidence only. Preserve negative results, version material changes, and distinguish regression repair from independent holdout or real-world validation.

Phase E is synthetic, balanced, and authored in the same repository. Phase F and F2 evaluate authority decisions only; they do not execute remediation. Authority policy v2 still relies on synthetic trust assertions and does not establish real-world source authenticity or production authorization.

See [METHODOLOGY.md](METHODOLOGY.md) for the broader experiment design and [results/README.md](results/README.md) for publication rules.
