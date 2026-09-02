from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from threading import RLock
from typing import Callable

from labs.adp_001.b2_baseline import Response, TinyApi


class CachedApi:
    def __init__(self, clock: Callable[[], float], ttl_seconds: int = 30, max_entries: int = 4) -> None:
        self._api = TinyApi()
        self._clock = clock
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._cache: OrderedDict[tuple[str, str], tuple[float, Response]] = OrderedDict()
        self._lock = RLock()

    def _copy_response(self, response: Response) -> Response:
        return Response(response.status, deepcopy(response.body))

    def put_item(self, client_id: str, key: str, value: str) -> Response:
        response = self._api.put_item(client_id, key, value)
        with self._lock:
            self._cache.pop((client_id, key), None)
        return response

    def get_item(self, client_id: str, key: str) -> Response:
        now = self._clock()
        cache_key = (client_id, key)
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None:
                expires_at, response = cached
                if now < expires_at:
                    self._cache.move_to_end(cache_key)
                    return self._copy_response(response)
                self._cache.pop(cache_key, None)

            response = self._api.get_item(client_id, key)
            if response.status == 200 and self._max_entries > 0:
                self._cache[cache_key] = (now + self._ttl_seconds, self._copy_response(response))
                self._cache.move_to_end(cache_key)
                while len(self._cache) > self._max_entries:
                    self._cache.popitem(last=False)
            return self._copy_response(response)
