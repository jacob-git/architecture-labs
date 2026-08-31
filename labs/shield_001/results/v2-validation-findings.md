# SHIELD Lab #001 — V2 Validation Findings

## Result

A clean repository execution of the committed SHIELD v2 validation passed all acceptance checks at repository commit `5a492909692891bacb564a9451b073a8478b0bef` with `dirty=False`.

The evidence preserves the experimental sequence rather than replacing it:

1. `shield-evidence-score-v1` passed the three fixed Phase A scenarios.
2. The frozen 1,782-profile Phase B adversarial suite exposed two v1 weaknesses: no sensitivity to gateway/path concentration and an adversarial ranking inversion.
3. `shield-evidence-score-v2` introduced concentration-aware effective source counts without weakening the frozen Phase B criteria.
4. The clean validation reproduced the v1 baseline, preserved Phase A, and passed all four frozen Phase B checks.

## Before and after

| Validation | V1 | V2 |
|---|---:|---:|
| Phase A fixed scenarios | PASS (3/3) | PASS (3/3) |
| Phase B frozen checks | FAIL (2/4) | PASS (4/4) |
| Phase B profiles | 1,782 | 1,782 |
| Concentration confidence drop | 0.000000 | 0.415455 |
| Adversarial ranking delta | +0.065347 | -0.349559 |

The direction change in the adversarial ranking is the key repair. Under v1, the 99%-concentrated high-volume case scored above the balanced independent reference. Under v2, it scores below the balanced reference while the Phase A behavior remains intact.

## Partial-correlation behavior

With four gateways and four paths held present while traffic concentration increases, v2 reduces the effective source count and confidence:

| Concentration | Effective gateways | Effective paths | Confidence |
|---:|---:|---:|---:|
| 25% | 4.000 | 4.000 | 0.950213 |
| 50% | 3.000 | 3.000 | 0.894598 |
| 75% | 1.714 | 1.714 | 0.723545 |
| 90% | 1.230 | 1.230 | 0.602327 |
| 99% | 1.020 | 1.020 | 0.534758 |

This directly addresses the Phase B finding that raw topology cardinality is not enough to represent evidence independence.

## What this supports

The result supports a narrow claim: for the committed synthetic scenarios and frozen stress suite, concentration-aware effective source counts repair the specific concentration blindness identified in `shield-evidence-score-v1` while preserving the earlier Phase A invariants.

## What this does not support

This is not independent real-world validation of SHIELD. V2 was designed after observing the Phase B counterexample. Inverse-Simpson effective counts measure distribution concentration but do not prove causal independence. The current lab remains synthetic and does not yet measure incident precision, recall, temporal decay, contradictory evidence, source reliability, or remediation safety.

## Publication provenance

Reviewed human-readable artifact:

- `v2-validation-2026-08-30-clean.summary.md`
- repository under test: `5a492909692891bacb564a9451b073a8478b0bef`
- repository dirty state: `false`
- frozen Phase B sweep digest: `121540fe542f5b93a40956a1d02ee99044ac1f84a3fc4c9a05607888e90365c4`

The generated JSON artifact was not supplied during this review, so this publication intentionally preserves only the reviewed Markdown summary and these findings. No JSON result has been reconstructed or inferred.

## Next experiment

Proceed to temporal evidence and decay only after preserving this v2 regression-repair result. The next phase should test confidence rise, evidence aging, recovery signals, stale-evidence decay, and recurrence without changing the v2 result recorded here.
