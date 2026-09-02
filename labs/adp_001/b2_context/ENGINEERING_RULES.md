# Engineering Rules

- Python standard library only for runtime code.
- Keep `TinyApi` as the authoritative backing store.
- Cache only successful reads.
- Invalidate affected entries on writes.
- Bound memory use explicitly.
- Protect shared cache state used by concurrent requests.
- Return independent response objects so callers cannot mutate cached state.
- Use the injected clock rather than wall clock time.
- Prefer the smallest implementation that satisfies the contract.
