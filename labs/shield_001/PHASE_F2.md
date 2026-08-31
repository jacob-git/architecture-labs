# SHIELD Lab #001 — Phase F2 Adversarial Remediation Authority

Phase F2 attacks the frozen `shield-remediation-authority-policy-v1` from Phase F. It does not modify temporal v3, Phase E labels, or the Phase F policy.

## Research question

Can the Phase F authority policy remain fail-closed when the metadata used to grant authority is stale, spoofed, contradictory, or unverified?

## Scientific rule

Phase F v1 is frozen before this suite. Phase F2 may fail.

A failure must be preserved. Do not weaken the adversarial safe bounds or silently change the policy in place. Any repair requires a new policy version and must keep Phase F and F2 unchanged.

## Trust-boundary model

Phase F consumes declared values for severity, reversibility, blast radius, and safety. Phase F2 adds a separate trusted-truth record so the harness can test what happens when those declarations are wrong.

This distinction is deliberate:

```text
declared metadata -> Phase F policy -> authority
trusted truth     -> maximum safe authority
```

The policy passes an adversarial case only when the granted authority is at or below the trusted safe bound.

## Frozen scenarios

1. spoofed critical severity on a non-incident;
2. irreversible action falsely declared reversible;
3. high blast radius falsely declared low;
4. stale critical-impact assertion;
5. contradictory safety signals collapsed into `safetyPass=True`;
6. rollback/reversibility asserted without verification;
7. explicit `safetyPass=False` baseline.

## Deterministic result

The current Phase F policy passes only **1/7** adversarial checks.

The explicit safety-failure baseline remains fail-closed. The other six cases exceed the frozen maximum-safe-authority bound because the policy assumes its authority metadata is already trustworthy.

The strongest counterexamples are:

- a synthetic non-incident with medium confidence can reach `mitigate` when severity is spoofed to critical;
- contradictory safety evidence can be collapsed to `safetyPass=True`, allowing a high-confidence critical incident to reach `isolate` even though the trusted safe bound is `observe`;
- unverified reversibility, blast radius, stale severity, and rollback assumptions can each permit `mitigate` when the safe bound is only `validate`.

## Interpretation

Phase F2 identifies a new architectural boundary: **safe authority depends not only on confidence and policy logic, but also on provenance, freshness, and verification of the policy inputs themselves.**

A future policy revision should not merely add more thresholds. It should make metadata trust explicit, for example through independently verified impact state, freshness limits, rollback verification, blast-radius attestation, and multi-source safety consensus.

## Limitations

- All truth and declared metadata are deterministic synthetic inputs.
- The suite does not implement cryptographic attestation or an external policy authority.
- The maximum-safe-authority labels are experimental assertions.
- No remediation action is executed.
