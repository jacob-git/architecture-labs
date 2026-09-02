from __future__ import annotations

from typing import Any

from labs.adp_001.b4_baseline import LegacyPublisher, Response, TinyApi


class PublishingApi:
    def __init__(self, publisher: LegacyPublisher) -> None:
        self._api = TinyApi()
        self._publisher = publisher

    def put_item(self, client_id: str, key: str, value: str) -> Response:
        response = self._api.put_item(client_id, key, value)
        if response.status == 200:
            envelope: dict[str, Any] = {
                "type": "item.updated",
                "client_id": client_id,
                "key": key,
                "value": value,
            }
            self._publisher.emit(envelope, channel="items.v1")
        return response

    def get_item(self, client_id: str, key: str) -> Response:
        return self._api.get_item(client_id, key)
