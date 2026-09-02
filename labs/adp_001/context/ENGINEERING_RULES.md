# ADP-001 Engineering Rules

1. Python 3.11 or newer.
2. Runtime implementation must use only the Python standard library.
3. Do not change existing response payloads or status codes for allowed requests.
4. Prefer composition over modifying baseline application behavior.
5. Make time deterministic through dependency injection.
6. Protect mutable shared rate-limit state from concurrent updates.
7. Keep the implementation local to the feature. Avoid unrelated refactors.
8. Tests must be deterministic and must not sleep.
9. Do not read or modify `tests_hidden.py` during an experiment run.
10. A solution is not complete merely because visible tests pass; the final diff must also comply with these rules.
