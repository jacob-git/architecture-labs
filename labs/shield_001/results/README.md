# SHIELD Lab #001 Results

Generated JSON and Markdown summaries are ignored by Git until reviewed.

## Reviewed publications

| Artifact | Status | Scope |
|---|---|---|
| [`v2-validation-2026-08-30-clean.summary.md`](v2-validation-2026-08-30-clean.summary.md) | PASS | Clean v2 regression validation at commit `5a492909692891bacb564a9451b073a8478b0bef` |
| [`v2-validation-findings.md`](v2-validation-findings.md) | Findings | Documents the v1 Phase B failure, v2 repair, evidence boundary, and next research step |

The reviewed v2 publication preserves the human-readable summary supplied from the clean run. The corresponding generated JSON artifact was not supplied for review and is therefore not published or reconstructed here.

## Review checklist

Before committing a result artifact:

1. run from a clean repository commit when possible;
2. run the complete unit test suite first;
3. verify `repositoryDirty` is `false` in the JSON artifact for a formal provenance claim;
4. verify every scenario or Phase B claim check, and explicitly classify failures rather than hiding them;
5. confirm scenario/sweep and scoring digests match the committed code;
6. record hardware, OS, Python version, and execution date from the artifact;
7. preserve negative or unexpected outcomes rather than retuning the scoring function in place;
8. publish limitations beside any reported result;
9. use immutable filenames for reviewed results rather than publishing a `latest` artifact.

## Version history policy

`shield-evidence-score-v1` is frozen as the scoring version that passed Phase A and failed two Phase B robustness checks. Do not alter v1 to make the negative result disappear.

`shield-evidence-score-v2` is a separate concentration-aware revision. Its validation must reproduce the v1 baseline, preserve all fixed Phase A outcomes, and pass the unchanged Phase B sweep before it is considered a successful regression repair.

Even a clean v2 pass is not real-world validation because v2 was designed after observing the Phase B counterexample. A reviewed v2 artifact should state that limitation beside the result.

Phase A is deterministic harness evidence only. Phase B is explicitly adversarial and may intentionally exit nonzero when the candidate score violates a predeclared check. A negative result should drive a new scoring version, not be rewritten away.
