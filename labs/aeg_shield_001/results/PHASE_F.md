# Phase F — Blind holdout against feedback-memory-v3

## Result

**feedback-memory-v3 passed 0 of 6 Phase F holdout checks.**

Phase E repaired the known Phase B and Phase D failure classes. Phase F froze v3 and then attacked trust and lifecycle assumptions that were not part of the v3 design.

| Holdout | Result | Exposed assumption |
|---|---|---|
| stolen signing key | fail | a valid MAC cannot distinguish the legitimate producer from an attacker who possesses the key |
| revoked key still accepted | fail | v3 has no key version, revocation time, or trust-lifecycle semantics |
| conflicting trusted producers | fail | recovery from one trusted producer can neutralize another producer's incident without a conflict policy |
| authenticated causal collision | fail | authentic records can still carry the wrong causal grouping |
| partial recovery erases full incident | fail | every recovery is treated as complete recovery |
| low-and-slow evidence flood | fail | authentication and a total cap do not provide rate, quota, or concentration controls |

## Interpretation

The Phase F result does not invalidate the Phase E properties that passed. It narrows the claim: v3 improves record integrity and replay resistance, but it does not establish trustworthy evidence governance when the trust root itself changes, trusted producers disagree, causal identity is wrong, recovery is partial, or authenticated evidence is strategically accumulated.

The most important architectural lesson is that **evidence authenticity is not evidence authority**. A record can be correctly signed and still be stale in authority, causally wrong, contradictory, incomplete, or abusive in aggregate.

## Reproduce

```bash
python -m unittest tests.test_aeg_shield_001_phase_f
python -m labs.aeg_shield_001.phase_f
```

The Phase F runner intentionally exits nonzero while any holdout fails. That exit is the experimental result, not a harness error.

## Next revision requirements

A future feedback-memory-v4 should add, at minimum:

1. key identity/version and revocation-time semantics
2. producer-specific authority scopes and conflict resolution
3. stronger causal identity than a producer-asserted source_event_id
4. explicit recovery completeness/coverage semantics
5. rate, quota, and concentration controls over accepted evidence
6. preservation of all frozen Phase A–F results as regression history

Any v4 repair should first pass the frozen known suites. A new blind holdout must then attack assumptions not used to design v4.
