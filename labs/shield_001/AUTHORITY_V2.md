# SHIELD Lab #001 — Remediation Authority Policy V2

`shield-remediation-authority-policy-v2` is a separate repair created after Phase F2 exposed that the Phase F authority policy trusted operational metadata too easily.

## Why v2 exists

Phase F separated confidence from severity and introduced bounded remediation authority. Phase F2 then showed that the policy could still authorize beyond the safe bound when declared metadata was wrong or stale:

- spoofed severity;
- falsely asserted reversibility;
- underestimated blast radius;
- stale impact data;
- contradictory safety signals collapsed into one `true` flag;
- rollback capability asserted without verification.

The problem is an **authority-input trust problem**, not a temporal-confidence problem.

## Authority Evidence Envelope

V2 introduces `shield-authority-evidence-envelope-v1` around every input that can increase authority.

Each authority-bearing input carries:

- value;
- source identity;
- trusted/untrusted status;
- verification status;
- age/freshness.

Safety additionally carries all required safety signals rather than a pre-collapsed boolean.

The current experimental freshness windows are:

| Domain | Maximum age |
|---|---:|
| severity / impact | 30 min |
| reversibility | 1,440 min |
| blast radius | 1,440 min |
| rollback capability | 1,440 min |
| safety consensus | 10 min |

These are lab parameters, not production recommendations.

## Fail-closed rules

1. Safety must be trusted, verified, fresh, non-empty, and unanimously passing. Otherwise authority is `observe`.
2. Severity, reversibility, and blast-radius evidence must each be trusted, verified, and fresh before they may increase authority. Otherwise authority is capped at `validate`.
3. Any `mitigate` or `isolate` authority that relies on reversibility requires independently verified rollback capability. Otherwise authority is capped at `validate`.
4. Temporal v3 confidence remains unchanged and is still only one input into authority.

## Frozen validation contract

The v2 validator must reproduce the previous history before accepting the repair:

- Phase F under policy v1 remains passing;
- Phase F2 under policy v1 remains `1/7`;
- Phase F scenarios remain unchanged;
- Phase F2 scenarios remain unchanged;
- policy v2 must satisfy all frozen Phase F expectations and all frozen F2 maximum-safe-authority bounds.

Passing this validation is regression-repair evidence only. It does not prove that real metadata sources are trustworthy or that autonomous remediation is safe.

## Reproduce

```bash
python3 -m unittest discover -s tests
python3 -m labs.shield_001.phase_f
python3 -m labs.shield_001.phase_f2
python3 -m labs.shield_001.authority_v2_validation
```

The validation runner writes:

```text
labs/shield_001/results/authority-v2-validation-latest.json
labs/shield_001/results/authority-v2-validation-latest.summary.md
```
