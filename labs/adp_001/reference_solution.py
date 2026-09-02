from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Callable

from labs.adp_001.baseline import Response, TinyApi


class RateLimitedApi:
    def __init__(self, clock: Callable[[], float], limit: int = 10, window_seconds: int = 60) -> None:
        self._api = TinyApi()
        self._clock = clock
        self._limit = limit
        self._window_seconds = window_seconds
        self._counts: dict[tuple[str, int], int] = defaultdict(int)
        self._lock = Lock()

    def _allowed(self, client_id: str) -> bool:
        bucket = int(self._clock() // self._window_seconds)
        key = (client_id, bucket)
        with self._lock:
            if self._counts[key] >= self._limit:
                return False
            self._counts[key] += 1
            return True

    def health(self, client_id: str) -> Response:
        if not self._allowed(client_id):
            return Response(429, {"error": "rate_limited"})
        return self._api.health()

    def put_item(self, client_id: str, key: str, value: str) -> Response:
        if not self._allowed(client_id):
            return Response(429, {"error": "rate_limited"})
        return self._api.put_item(key, value)

    def get_item(self, client_id: str, key: str) -> Response:
        if not self._allowed(client_id):
            return Response(429, {"error": "rate_limited"})
        return self._api.get_item(key)
