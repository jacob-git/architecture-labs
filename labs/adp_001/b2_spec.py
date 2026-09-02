from __future__ import annotations

FEATURE = {
    "name": "per-client bounded TTL response cache",
    "ttl_seconds": 30,
    "max_entries": 4,
    "properties": [
        "successful reads may be cached",
        "cache entries are isolated by client identity and key",
        "writes invalidate the affected client's cached key immediately",
        "entries expire after 30 seconds using the injected clock",
        "cache size is bounded to at most 4 entries",
        "concurrent reads are safe",
        "404 responses are not retained as durable cache entries",
        "returned responses cannot mutate cached state",
        "legacy response status and payloads are preserved",
        "runtime uses only the Python standard library",
    ],
}
