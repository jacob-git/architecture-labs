# SHIELD Lab #001 — V2 Validation Summary

**Overall:** PASS  
**Repository:** `5a492909692891bacb564a9451b073a8478b0bef` (dirty=False)  
**Frozen sweep:** `121540fe542f5b93a40956a1d02ee99044ac1f84a3fc4c9a05607888e90365c4`  
**V1:** `shield-evidence-score-v1`  
**V2:** `shield-evidence-score-v2`

## Before and after

| Validation | V1 | V2 |
|---|---:|---:|
| Phase A fixed scenarios | PASS (3/3) | PASS (3/3) |
| Phase B frozen checks | FAIL (2/4) | PASS (4/4) |
| Phase B profiles | 1,782 | 1,782 |
| Concentration drop | 0.000000 | 0.415455 |
| Adversarial ranking delta | 0.065347 | -0.349559 |

## V2 partial-correlation sweep

| Requested concentration | Effective gateways | Effective paths | Confidence |
|---:|---:|---:|---:|
| 0.25 | 4.000 | 4.000 | 0.950213 |
| 0.50 | 3.000 | 3.000 | 0.894598 |
| 0.75 | 1.714 | 1.714 | 0.723545 |
| 0.90 | 1.230 | 1.230 | 0.602327 |
| 0.99 | 1.020 | 1.020 | 0.534758 |

## Validation checks

- PASS — `v1BaselinePreserved`
- PASS — `v2PreservesPhaseA`
- PASS — `v2PassesFrozenPhaseB`
- PASS — `frozenSweepSizePreserved`

## Interpretation

V2 is accepted by this validation only if the original v1 outcome is reproduced, all fixed Phase A scenarios still pass, and the unchanged 1,782-profile Phase B stress suite passes without weakening its criteria.

## Limitations

- V2 was designed in direct response to the Phase B concentration counterexample, so passing that frozen suite is evidence of regression repair, not independent real-world validation.
- Inverse-Simpson effective counts measure distribution concentration but do not prove causal independence.
- The experiment remains synthetic and does not measure incident precision, recall, temporal decay, or remediation safety.
