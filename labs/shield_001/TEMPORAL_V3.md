# SHIELD Temporal Evidence V3

`shield-temporal-evidence-v3` is a separate revision created after the Phase D holdout exposed two weaknesses in temporal v2.

Temporal v2 remains frozen. Phase C, Phase C2, and Phase D remain unchanged.

## Why v3 exists

The post-v2 Phase D holdout exposed two new counterexamples:

1. two unrelated failure fingerprints that were individually medium-confidence combined into one high-confidence result;
2. a small fresh episode was promoted from medium to high when a few different topology units carried very large but four-half-life-old failure episodes.

Those failures were not part of the temporal-v2 repair target.

## Revision 1 — fingerprint partitions

V3 scores each fingerprint independently.

```text
events
  -> partition by fingerprint
  -> temporal scoring inside each partition
  -> retain every partition score
  -> overall confidence = max(partition confidence)
```

Unrelated fingerprints therefore remain independently visible but cannot increase one another's incident confidence.

The selected fingerprint is deterministic; ties are broken by fingerprint string. The full `fingerprintScores` map remains in the result.

This assumes the fingerprint is the incident-evidence partition key for this experiment. That assumption still requires future validation.

## Revision 2 — episode-volume-weighted freshness

Temporal v2 calculates freshness as the average freshness of active evidence units. That is safe when units have comparable episode sizes, but Phase D showed that a few stale units with very large current episodes can saturate the global observation-strength term while only modestly reducing unit-average freshness.

V3 keeps v2's current-episode semantics but weights freshness by the episode volume represented by each active unit.

For active unit `i`:

```text
w_i = 0.5 ** (age_i / half_life)
e_i = failures in the unit's latest failure episode

freshness_factor =
    sum(e_i * w_i) / sum(e_i)
```

The existing observation-strength, topology-diversity, source-support, and confidence mappings remain otherwise unchanged.

When all active units have equal episode sizes, this is exactly the temporal-v2 freshness factor. That preserves the Phase C confidence trajectory.

## Frozen validation contract

The temporal-v3 validation runner does not change prior suites.

It must reproduce:

```text
temporal v2
Phase C  -> 7/7 PASS
Phase C2 -> 7/7 PASS
Phase D  -> 5/7 FAIL
```

V3 is accepted by this regression only if:

```text
temporal v3
Phase C  -> 7/7 PASS
Phase C2 -> 7/7 PASS
Phase D  -> 7/7 PASS
```

The Phase C numeric confidence trajectory is also compared directly between temporal v2 and temporal v3.

## Interpretation boundary

A v3 pass is not a second independent holdout result. V3 was designed after observing the Phase D failures, so passing Phase D is regression-repair evidence.

The next meaningful test should use new scenarios, noisy ground truth, or external/open traces that were not used to design v3.

## Limitations

- Fingerprint partitioning depends on fingerprint quality and does not prove causal incident identity.
- Selecting maximum partition confidence is an experimental aggregation policy, not a production recommendation.
- Episode-volume-weighted freshness can reduce confidence when a small fresh episode coexists with a much larger stale episode; that conservative behavior needs independent calibration.
- The 30-minute half-life remains an experimental parameter.
- No source trust, signed telemetry, noisy ground truth, or remediation authority is evaluated here.
