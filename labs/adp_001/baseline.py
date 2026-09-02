from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Response:
    status: int
    body: dict[str, object]


class TinyApi:
    """Small deterministic baseline used by ADP-001.

    Phase A intentionally has no rate limiting. Later experiment modes modify a
    copy of this baseline to satisfy the same feature goal under different AI
    development patterns.
    """

    def __init__(self) -> None:
        self._items: dict[str, str] = {}

    def health(self) -> Response:
        return Response(200, {"status": "ok"})

    def put_item(self, key: str, value: str) -> Response:
        if not key:
            return Response(400, {"error": "key_required"})
        self._items[key] = value
        return Response(200, {"key": key, "value": value})

    def get_item(self, key: str) -> Response:
        if key not in self._items:
            return Response(404, {"error": "not_found"})
        return Response(200, {"key": key, "value": self._items[key]})
