from __future__ import annotations

from labs.adp_001.b4_candidate_loader import publishing_api_type


class RuntimePublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, object], str]] = []

    def emit(self, envelope: dict[str, object], /, *, channel: str) -> None:
        self.calls.append((dict(envelope), channel))


def test_successful_put_publishes_runtime_event() -> None:
    publisher = RuntimePublisher()
    api = publishing_api_type()(publisher)
    response = api.put_item("client-a", "x", "1")
    assert response.status == 200
    assert publisher.calls == [(
        {"type": "item.updated", "client_id": "client-a", "key": "x", "value": "1"},
        "items.v1",
    )]


def test_existing_read_behavior_still_works() -> None:
    publisher = RuntimePublisher()
    api = publishing_api_type()(publisher)
    api.put_item("client-a", "x", "1")
    assert api.get_item("client-a", "x").body == {"key": "x", "value": "1"}
