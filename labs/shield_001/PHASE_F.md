# SHIELD Lab #001 — Phase F Confidence, Severity, and Remediation Authority

Phase F is the first SHIELD experiment that separates **what the system has enough evidence to believe** from **what action it is allowed to take**.

Temporal v3 remains frozen. Phase E remains frozen, including its three shared-cause false negatives.

## Research question

Can a risk-governed authority policy respond appropriately to high-impact incidents even when evidentiary confidence is only medium, without granting broad or irreversible remediation authority?

## Inputs

Phase F evaluates remediation authority as a function of:

- SHIELD confidence from `shield-temporal-evidence-v3`;
- severity/impact;
- reversibility;
- blast radius;
- explicit safety-gate result.

Confidence and severity are deliberately independent. A correlated real outage may have high severity and only medium evidentiary confidence.

## Authority ladder

The experimental ladder is:

1. `observe`
2. `enrich`
3. `validate`
4. `mitigate`
5. `isolate`
6. `recover`

The ladder represents increasing authority, not mandatory actions.

## Policy boundaries

The frozen candidate policy uses these boundaries:

- failed safety gate -> `observe`;
- no active evidence -> `observe`;
- low confidence cannot directly authorize intervention;
- medium confidence may authorize **bounded reversible mitigation** only for critical severity with low/medium blast radius and passing safety;
- medium confidence can never authorize `isolate` or `recover`;
- high confidence plus high/critical impact can authorize bounded mitigation/isolation when reversible and blast radius is constrained;
- irreversible or high-blast-radius changes are capped at `validate` even with high confidence.

This is intentionally conservative.

## Why Phase E matters

Phase E showed three real synthetic incidents that remained below the high-confidence boundary:

- `I10` — shared gateway;
- `I11` — shared path;
- `I12` — shared gateway and path.

Phase F does not re-label those as high confidence. Instead it asks whether severity and safety can raise **urgency and bounded authority** without corrupting the evidence score.

The frozen Phase F expectations are:

- `I10` and `I11`: medium confidence + critical severity + reversible bounded action -> `mitigate`;
- `I12`: medium confidence + critical severity + irreversible/high-blast action -> `validate`;
- non-incidents never receive `mitigate` or higher;
- safety failure always caps authority at `observe`.

## Interpretation boundary

A Phase F pass does **not** mean SHIELD can autonomously remediate production incidents. No real action executes in this lab. The result would show only that the committed candidate policy preserves the intended separation between evidence confidence, impact, and execution authority in the frozen synthetic scenarios.

The next stronger test after Phase F is adversarial authority testing: incorrect severity labels, unsafe rollback assumptions, stale impact signals, conflicting policy inputs, and blast-radius misclassification.
