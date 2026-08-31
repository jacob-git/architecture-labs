# SHIELD Lab #001 — Phase E Noisy Ground Truth & Calibration

Phase E is the first SHIELD lab phase with explicit synthetic incident and non-incident labels.

It evaluates the frozen `shield-temporal-evidence-v3` model. Temporal v3 is not changed by this phase.

## Research question

When a deterministic corpus contains persistent incidents, recurrence, shared-cause incidents, localized retry noise, unrelated fingerprints, recovery, stale evidence, contradictory evidence, and future-dated telemetry, how well does the frozen SHIELD high-confidence boundary separate incident from non-incident cases?

## Scientific rule

The existing SHIELD high-confidence boundary remains fixed at `0.75`.

Phase E does not search for a better threshold after seeing the labels. A failing metric is preserved as evidence rather than repaired by changing the corpus, threshold, or temporal v3 in place.

## Corpus

The corpus contains 24 deterministic cases: 12 labeled incidents and 12 labeled non-incidents.

Incident cases include broad persistent incidents, gradual distributed incidents, recurrence after recovery, fresh evidence mixed with stale unrelated-fingerprint noise, and real shared-cause incidents whose observations share a gateway, a path, or both.

Non-incident cases include localized retry bursts, unrelated fingerprints, recovered histories, delayed pre-recovery telemetry, same-timestamp contradiction, stale evidence, and future-only telemetry.

The labels are authored independently of temporal v3's output. The three shared-cause cases remain labeled as real incidents even if SHIELD assigns them less than high confidence.

## Frozen acceptance criteria

At the existing `0.75` high-confidence boundary:

- precision >= `0.90`;
- recall >= `0.80`;
- false-positive rate <= `0.10`;
- Brier score <= `0.15`;
- expected calibration error <= `0.15`;
- median time to high confidence among detected incidents <= `15` minutes.

The corpus must remain balanced at 12 incident and 12 non-incident cases.

Brier score and ECE are exploratory diagnostics. SHIELD confidence has not been established as a calibrated probability of incident occurrence.

## Deterministic dry-run result

```text
TP = 9
FP = 0
TN = 12
FN = 3

precision = 1.000
recall    = 0.750
FPR       = 0.000
F1        = 0.857

Brier score ≈ 0.092
ECE         ≈ 0.110
```

Detected incidents reach high confidence with a median delay of `0` minutes and a maximum delay of `15` minutes.

Overall Phase E result:

```text
PASS 6 / 7 checks
FAIL recallAtLeast80Percent
```

The three false negatives are:

- `I10` — real incident sharing one gateway;
- `I11` — real incident sharing one path;
- `I12` — real incident sharing both gateway and path.

## Interpretation

This is an important boundary rather than a reason to lower the high-confidence threshold.

SHIELD deliberately separates **confidence** from **severity**. A real incident can exist while the available evidence remains causally concentrated. If high SHIELD confidence is treated as an incident-detector boundary, that conservatism becomes measurable as false negatives.

Phase E therefore does not establish that temporal v3 is a complete incident detector. On this balanced synthetic corpus, the high-confidence boundary is highly precise but misses some real shared-cause incidents.

## Limitations

- Ground truth is synthetic, authored in the same repository, and not blinded.
- The corpus is balanced, unlike most production incident streams.
- Confidence is not a validated probability, so calibration metrics are exploratory.
- Low confidence on the shared-cause cases may still be epistemically appropriate even though those cases count as detector false negatives.
- No incident severity, source reliability, blast radius, remediation authority, signed telemetry, or real trace replay is modeled.
- No threshold optimization is performed in Phase E.

## Reproduction

```bash
python3 -m unittest discover -s tests
python3 -m labs.shield_001.phase_e
```

Outputs:

```text
labs/shield_001/results/phase-e-latest.json
labs/shield_001/results/phase-e-latest.summary.md
```

A nonzero exit is expected while the frozen recall criterion fails.
