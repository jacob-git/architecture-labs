# SHIELD Lab #001 Results

Generated JSON and Markdown summaries are ignored by Git until reviewed.

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

Phase A is deterministic harness evidence only. Phase B is explicitly adversarial and may intentionally exit nonzero when the candidate score violates a predeclared check. A negative result should drive a new scoring version, not be rewritten away.
