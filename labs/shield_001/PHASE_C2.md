# SHIELD Lab #001 — Phase C2 Adversarial Temporal Robustness

Phase C2 attacks the frozen `shield-temporal-evidence-v1` model introduced in Phase C. It does not modify that model.

A Phase C2 failure is a valid result. Counterexamples remain part of the record and should drive an explicitly versioned temporal-model revision rather than changes to the adversarial criteria.

## Research question

Can the Phase C temporal model remain conservative and interpretable when telemetry is mixed across fingerprints, delayed, stale, bursty, future-dated, or contradictory?

## Frozen target

```text
temporal model: shield-temporal-evidence-v1
base scoring:   shield-evidence-score-v2
```

## Adversarial checks

1. **Cross-fingerprint recovery isolation** — recovery for `dependency-y-timeout` must not materially suppress `dependency-x-timeout`; maximum allowed confidence drop is `0.02`.
2. **Mixed stale-history amplification** — 100 stale failures per unit must not raise a fresh state by more than `0.05` or promote it into high confidence.
3. **Delayed recovery arrival** — an older recovery supplied after a newer failure in input order must not erase the newer failure.
4. **Bursty single-unit recurrence** — 500 failures from one evidence unit must remain low-confidence.
5. **Future clock-skew visibility** — +2 minute future-dated evidence must not be silently indistinguishable from empty input; the eventual handling policy may reject, quarantine, clamp, or tolerate bounded skew.
6. **Same-timestamp contradiction visibility** — tied failure and recovery must remain distinguishable from clean recovery-only evidence.
7. **Contradictory input-order invariance** — reversing the same contradictory event set must not change detector output.

Phase C2 reports each property independently and exits nonzero when any property fails.

## Reproduction

```bash
python3 -m unittest discover -s tests
python3 -m labs.shield_001.phase_c2
```

Generated artifacts:

```text
labs/shield_001/results/phase-c2-latest.json
labs/shield_001/results/phase-c2-latest.summary.md
```

## Threats to validity

- These are deterministic synthetic distributed-telemetry scenarios.
- Fingerprint isolation could be enforced upstream rather than inside the detector, but that contract must then be explicit and tested.
- The `0.02` and `0.05` thresholds are stress criteria, not universal calibration values.
- Clock-skew visibility does not prescribe a specific skew policy.
- Contradiction visibility does not prescribe which signal should win.
- No source trust, signed telemetry, network-delay distribution, incident ground truth, or remediation action is modeled.
