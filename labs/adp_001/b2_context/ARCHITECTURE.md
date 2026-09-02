# Architecture

The baseline is deliberately small. Preserve the existing `TinyApi` as the source of truth for item storage and legacy response behavior. Add caching as a wrapper rather than duplicating storage semantics.

Cache identity must include both client identity and item key. Time based behavior must use the injected clock so tests remain deterministic.
