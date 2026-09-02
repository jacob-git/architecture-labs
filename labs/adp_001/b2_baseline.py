from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Response:
    status: int
    body: dict[str, str]


class TinyApi:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], str] = {}

    def put_item(self, client_id: str, key: str, value: str) -> Response:
        self._items[(client_id, key)] = value
        return Response(200, {"key": key, "value": value})

    def get_item(self, client_id: str, key: str) -> Response:
        value = self._items.get((client_id, key))
        if value is None:
            return Response(404, {"error": "not_found"})
        return Response(200, {"key": key, "value": value})
