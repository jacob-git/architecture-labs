# Intent Driven Prompt

## Outcome
Improve repeated read performance without allowing cached data to become incorrect, unsafe, or unbounded.

## Constraints
- Cache successful item reads for up to 30 seconds.
- Keep cache entries isolated by client identity and key.
- Writes must make later reads return the newly written value immediately.
- Keep the cache bounded to at most 4 entries.
- Preserve existing API status codes and response payloads.
- Use only the Python standard library.
- Keep behavior safe under concurrent reads.
- Add automated tests.

Choose an implementation that fits the existing codebase and remains easy to reason about.
