# SHIELD Lab #001 — Phase D Temporal Holdout Generalization

Phase D is the first post-repair temporal suite created after `shield-temporal-evidence-v2` was frozen.

Its purpose is not to prove production validity. It asks whether temporal v2 generalizes beyond the Phase C and C2 cases that shaped its design.

## Scientific rule

Temporal v2 is frozen before Phase D. Phase D may fail.

A Phase D failure must be preserved as evidence. Do not weaken the holdout thresholds or silently modify temporal v2 after observing the result. Any material repair requires a new temporal model version and must keep Phase C, C2, and D frozen.

## Holdout checks

Phase D adds seven new invariants:

1. **Mixed fingerprints do not mutually reinforce.** Two unrelated failure fingerprints are scored separately and together. If neither fingerprint reaches high confidence on its own, combining them must not create a high-confidence incident, and combined confidence may exceed the stronger component by at most `0.05`.
2. **Stale diverse units cannot escalate fresh evidence.** Nine fresh evidence units with one failure each are compared with the same fresh evidence plus three four-half-life-old topology units carrying 100 failures each. The stale units may increase confidence by at most `0.05` and may not promote the fresh state into a higher authority tier.
3. **Time translation invariance.** Adding the same constant offset to every timestamp and the evaluation time must not change the detector output.
4. **Delayed pre-recovery replay is ignored.** Telemetry replay carrying a timestamp older than a later recovery must not reopen a recovered episode.
5. **Repeated recovery is idempotent.** Repeating recovery signals without a later failure must not change the final confidence state.
6. **Future telemetry does not alter current confidence.** Future-dated evidence must remain excluded from the current score while its skew remains visible diagnostically.
7. **Post-recovery recurrence starts fresh.** A large historical incident followed by recovery and then a fresh recurrence must score identically to that fresh recurrence without the historical timeline.

## Current holdout result

The deterministic dry run produces five passing checks and two failures.

### Counterexample 1 — cross-fingerprint reinforcement

Two unrelated fingerprints each score at approximately `0.601` (`medium`) when evaluated alone.

When their evidence is combined, temporal v2 scores approximately `0.935` (`high`).

The model is fingerprint-aware for recovery identity, but its aggregate confidence calculation still pools active evidence units across fingerprints. This means unrelated failure classes can reinforce one another unless an upstream partitioning invariant is guaranteed.

### Counterexample 2 — stale diversity amplification

Nine fresh units with one failure each score approximately `0.478` (`medium`).

Adding three stale topology units from four half-lives earlier, each with 100 failures in its latest episode, raises confidence to approximately `0.822` (`high`).

Temporal v2 repaired stale-history amplification when stale and fresh failures occur on the same evidence units. This holdout shows that stale evidence on different active units can still inflate the global episode-volume and diversity terms enough to escalate the fresh state.

## Interpretation boundary

This is stronger than another regression-repair pass because Phase D was not part of temporal v2's repair target. It is still not an external or blinded validation: the scenarios were designed after v2 was frozen by inspecting model semantics.

The correct next step after a Phase D failure is to preserve this result and design an explicitly versioned temporal v3 candidate. That candidate must pass frozen Phase C, Phase C2, and Phase D without weakening any of them.
