# Phase E — Feedback Memory v3 Repair

Phase D was intentionally designed after feedback-memory-v2 had been frozen. It broke v2 on all five unseen holdout checks. Phase E introduces a separate `feedback-memory-v3` implementation; v1 and v2 remain unchanged in the repository.

## Repair objective

Preserve the useful governance feedback demonstrated in Phase A while repairing the failure classes exposed by Phases B and D:

- stale evidence
- environment contamination
- untrusted producer input
- unbounded aggregation
- future timestamps / clock skew
- correlation-ID evasion
- replay under changed event IDs
- producer-name spoofing
- missing recovery / counter-evidence semantics

## v3 controls

1. **Authenticated producer evidence** — evidence is accepted only when an HMAC signature verifies against a configured producer key.
2. **Verified source-event identity** — multiple symptoms linked to the same signed `source_event_id` contribute at most one incident penalty.
3. **Replay resistance** — duplicate event IDs and duplicate signed payloads are rejected at ingestion.
4. **Temporal validity** — evidence beyond the allowed future clock-skew window is rejected; old evidence still decays and eventually expires.
5. **Environment scope** — evidence remains isolated by environment.
6. **Bounded aggregation** — accepted incident penalty is capped.
7. **Lifecycle evidence** — a later verified recovery record for the same source event neutralizes that incident's active penalty.

## Frozen repair validation

`phase_e.py` encodes ten deterministic properties:

| Property | Expected v3 behavior |
|---|---|
| original learning preserved | severe trusted runtime evidence can still change allow to deny |
| stale evidence | ignored after expiry window |
| environment contamination | isolated |
| untrusted producer | rejected |
| bounded aggregation | capped |
| future timestamp | rejected at ingestion |
| correlation-ID evasion | same verified source event counted once |
| replay with new event ID | duplicate signed payload rejected |
| trusted producer-name spoof | invalid signature rejected |
| verified recovery | later signed recovery neutralizes linked incident penalty |

The test `tests/test_aeg_shield_001_phase_e.py` freezes these expectations.

## Important claim boundary

The HMAC mechanism is an experimental stand-in for authenticated evidence provenance. It demonstrates that **producer-name allowlisting is insufficient and verifiable authenticity changes the result**. It is not a production key-management design.

A malicious actor who actually obtains a trusted signing key can still create records that this lab accepts. Key compromise, revocation, rotation, signer quorum, hardware-backed identity, and transparency logs remain untested.

Likewise, `source_event_id` is stronger here because it is part of the authenticated payload, but the lab does not yet prove that the producer assigned the correct real-world causal identity.

## Reproduce

```bash
python -m unittest tests.test_aeg_shield_001_phase_e
python -m labs.aeg_shield_001.phase_e
```

## Next stage

Freeze feedback-memory-v3 and design a new holdout phase without modifying v3. Candidate attacks include:

- legitimate signing-key compromise and revocation timing
- conflicting evidence from two independently trusted producers
- source-event identity collision or incorrect causal grouping by an authenticated producer
- recovery-before-incident ordering and delayed telemetry
- partial recovery versus full recovery
- evidence flooding below replay-detection similarity

Phase E repairs known failure classes. It is not independent validation of v3 against unseen attacks.
