# SHIELD Temporal Evidence V2

## Why this version exists

Phase C established useful temporal behavior for `shield-temporal-evidence-v1`: confidence accumulated with fresh corroboration, decayed with age, fell after recovery, rebuilt on recurrence, ignored future evidence for current confidence, resisted a fully stale 5,000-event incident, and remained input-order invariant.

Phase C2 then attacked that frozen model and exposed four weaknesses:

1. a recovery for a different failure fingerprint could erase an unrelated active failure sharing the same topology;
2. stale historical failures could inflate the global observation-strength term when fresh evidence existed on the same units;
3. future-dated telemetry was silently indistinguishable from no telemetry;
4. same-timestamp failure and recovery became indistinguishable from recovery-only input.

Those Phase C2 failures remain part of the record. Temporal v2 is a separate model revision.

## Design changes

### Fingerprint-aware evidence identity

Temporal v1 grouped an evidence unit as:

```text
(app, region, cluster, gateway, path)
```

Temporal v2 uses:

```text
(fingerprint, app, region, cluster, gateway, path)
```

A recovery for one fingerprint therefore cannot supersede failures belonging to another fingerprint solely because their topology matches.

### Current failure episode for observation strength

Temporal v1 retained every surviving failure after the latest recovery when calculating `activeFailureEvents`. That count fed the global saturation term. In a mixed stale + fresh timeline, a large stale history could therefore make a small fresh recurrence look much stronger than the fresh evidence alone.

Temporal v2 keeps the full surviving failure count as a diagnostic but calculates observation strength from each active unit's **current failure episode**: failures at that unit's most recent failure timestamp.

```text
activeFailureEvents
    = all surviving failures after recovery

activeEpisodeFailureEvents
    = failures at each active unit's latest failure timestamp

observation_strength
    = 1 - exp(-activeEpisodeFailureEvents / saturation_events)
```

This preserves the original Phase C scenarios because their repeated evidence within each unit is already emitted at the same episode timestamp, while preventing old episodes from amplifying a newer recurrence.

The most-recent-timestamp episode definition is deliberately simple and remains a threat to validity. Real telemetry may require explicit incident/session identifiers or a bounded episode window.

### Future timestamp diagnostics

Events later than the evaluation time still contribute zero confidence. Temporal v2 additionally reports:

```text
futureEventCount
maxFutureSkewMinutes
```

This makes clock skew or future-dated input visible without silently granting it evidence authority. The model does not yet prescribe rejection, clamping, tolerance windows, or quarantine policy.

### Same-timestamp contradiction diagnostics

Recovery continues to win a failure/recovery timestamp tie for confidence, preserving the Phase C recovery rule. Temporal v2 additionally reports:

```text
timestampConflictUnits
```

A contradictory tie is therefore distinguishable from a clean recovery-only state. This is observability of ambiguity, not a claim that recovery should universally win in production.

## Frozen validation contract

Temporal v2 does not change Phase C or Phase C2 scenarios, thresholds, or expected properties.

The validation must reproduce:

```text
temporal v1
Phase C  = PASS 7/7
Phase C2 = FAIL 3/7
```

Temporal v2 is accepted by this regression only if:

```text
temporal v2
Phase C  = PASS 7/7
Phase C2 = PASS 7/7
```

The validation also requires the selected Phase C confidence values to remain numerically identical and the Phase C/C2 scenario digests to remain unchanged.

## Evidence boundary

A temporal v2 pass is regression-repair evidence only. The model was designed after observing the Phase C2 counterexamples.

It does not establish:

- correct production half-life calibration;
- correct real-world incident episode boundaries;
- trustworthy fingerprint generation;
- clock synchronization policy;
- source reliability or signed telemetry;
- incident precision or recall;
- remediation authority or action safety.

Those require independent holdout scenarios, noisy ground truth, realistic delayed-telemetry distributions, and eventually open or consented trace replay.
