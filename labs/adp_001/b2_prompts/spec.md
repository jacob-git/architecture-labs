# Spec Driven Prompt

Implement a per-client bounded TTL response cache around the existing API.

## Functional requirements
1. Cache successful `get_item` responses for 30 seconds.
2. Cache identity is `(client_id, key)`.
3. A `put_item` must invalidate any cached value for that same client and key before a later read can return stale data.
4. Cache only successful reads; do not retain 404 responses as durable cache entries.
5. Cache capacity must never exceed 4 entries. Evict the least recently used entry when necessary.
6. At the exact TTL boundary an entry is expired.
7. Concurrent reads must not corrupt cache state or return inconsistent results.
8. A caller mutating a returned response body must not mutate cached state.
9. Preserve existing status codes and response payloads.

## Engineering constraints
- Constructor: `CachedApi(clock, ttl_seconds=30, max_entries=4)`.
- Methods: `put_item(client_id, key, value)` and `get_item(client_id, key)`.
- Python standard library only.
- Use the injected clock for TTL behavior.

## Acceptance criteria
- Existing API behavior remains compatible.
- Visible tests pass.
- No third party runtime dependency is introduced.
- The implementation is safe under concurrent reads.
