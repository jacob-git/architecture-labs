# ADP-001 Architecture Context

The baseline is intentionally small. `TinyApi` owns application behavior and returns the immutable `Response` value object.

For the rate limiting experiment:

- Rate limiting is a boundary concern. Keep it outside `TinyApi` rather than mixing request accounting into application storage logic.
- Preserve `TinyApi` behavior so compatibility can be evaluated independently from the new boundary policy.
- Time must be injectable. Do not call wall clock time directly inside logic that must be deterministically tested.
- Per-client request accounting may be shared across calls, but updates must be safe under concurrent access.
- A rejected request must not execute the underlying application operation.
