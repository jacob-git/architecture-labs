# Phase D — Blind Holdout Attack

## Frozen implementation

`feedback-memory-v2` was frozen before this phase. Phase D adds new adversarial cases only.

## Holdout result

**0 / 5 holdout checks passed.**

The v2 repair fixed every declared Phase B counterexample, but it did not generalize to five previously untested assumptions.

| Holdout | Expected | Observed | Result |
|---|---|---|---|
| Future timestamp | ignore/quarantine | treated as fresh and denied | fail |
| Correlation-ID evasion | one root cause should not double count | forged IDs accumulated | fail |
| Replay with new IDs | one incident should not gain repeated weight | replay accumulated to cap | fail |
| Trusted producer compromise | compromised identity should not be sufficient | record accepted and governed | fail |
| Missing counter-evidence | verified recovery should be representable | negative evidence remained one-way | fail |

## What broke

### 1. Freshness was not the same as temporal validity

V2 decayed old evidence but clamped negative age to zero. A record dated far in the future therefore received full weight. A production design needs an explicit admissible clock-skew window and quarantine behavior.

### 2. Correlation identity was still an assertion

V2 deduplicated by `correlation_id`, but trusted the field itself. A single root cause presented under multiple IDs bypassed the protection.

### 3. Bounded aggregation limited damage but did not stop replay

The `0.60` cap prevented unbounded growth, but replayed copies with new IDs still reached the cap and changed governance.

### 4. Producer allowlisting was identity, not authenticity

A record naming `shield-runtime` was accepted. V2 has no signature, attestation, nonce, sequence, or integrity proof, so compromise or spoofing of a trusted producer remains outside its protection.

### 5. Memory was one-way

V2 can only add negative incident evidence. It cannot represent verified recovery, contradiction, revocation, supersession, or counter-evidence. That makes governance memory structurally biased toward accumulated negative history.

## Claim boundary

Phase C remains valid for the exact six repair checks it passed. Phase D demonstrates that those repairs were not sufficient to establish robust evidence integrity under unseen attacks.

## Required next revision

A future v3 should be designed only after preserving this holdout suite unchanged. Likely controls include:

- explicit future-clock tolerance and quarantine
- server-derived or independently validated incident identity
- replay-resistant event identity / nonce / sequence semantics
- cryptographic or attested producer authenticity
- evidence lifecycle states: active, superseded, revoked, recovered
- explicit counter-evidence with conservative conflict resolution

The next revision must pass Phase A, frozen Phase B, Phase C regression checks, and this frozen Phase D holdout without changing expected outcomes.
