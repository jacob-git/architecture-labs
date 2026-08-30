# SHIELD Lab #001 Results

Generated JSON results are ignored by Git until reviewed.

## Review checklist

Before committing a result artifact:

1. run from a clean repository commit;
2. run the complete unit test suite first;
3. verify `repositoryDirty` is `false` in the JSON artifact;
4. verify all scenario and claim checks pass or explicitly classify each failure;
5. confirm the scenario and scoring digests match the committed code;
6. record hardware, OS, Python version, and execution date from the artifact;
7. preserve negative or unexpected outcomes rather than retuning the scoring function in place;
8. publish limitations beside any reported result.

A deterministic Phase A pass is harness evidence only. It does not establish real-world SHIELD effectiveness.
