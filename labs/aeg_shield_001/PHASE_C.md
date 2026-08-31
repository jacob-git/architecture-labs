# Phase C — Feedback Memory v2 Repair

Phase B demonstrated that feedback-memory-v1 was mechanically effective but unsafe as a governance input. It failed all four adversarial integrity checks because evidence had no freshness, environment, correlation, or producer authority boundaries.

## Repair objective

Feedback-memory-v2 must preserve the useful Phase A behavior while repairing every frozen Phase B counterexample without modifying those counterexamples.

## Changes in v2

1. **Trusted provenance** — only configured evidence producers may mutate memory.
2. **Environment scope** — evidence is evaluated only inside the environment where it occurred.
3. **Correlation identity** — multiple symptoms sharing one correlation ID contribute once, using the strongest severity.
4. **Freshness and decay** — evidence influence decays exponentially with a 30-day experimental half-life and is ignored after six half-lives.
5. **Bounded aggregation** — total learned penalty is capped at 0.60.

These are experimental constants, not production recommendations.

## Validation suite

Phase C evaluates six properties:

| Check | Expected |
|---|---|
| Phase A learning preserved | severe trusted current evidence can still change allow → deny |
| Stale evidence | 180-day-old evidence does not deny the proposal |
| Correlated symptoms | two symptoms from one root cause do not double-count |
| Environment contamination | prod evidence does not govern staging |
| Poisoned feedback | untrusted producer evidence is rejected |
| Bounded aggregation | repeated independent evidence cannot exceed the configured cap |

Run:

```bash
python -m labs.aeg_shield_001.phase_c
```

The implementation is deliberately separate from `core.py`. Phase A and Phase B remain frozen so the research record shows the original successful mechanism, the v1 failure, and the v2 repair independently.

## Claim boundary

Passing this repair suite would show only that feedback-memory-v2 repairs the known Phase B counterexamples while preserving the original learning property. It would not establish that the design survives unseen attacks.

The next required stage is a holdout adversarial Phase D designed after v2 is frozen.
