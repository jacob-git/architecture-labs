from __future__ import annotations

from labs.adp_001.b4_candidate_loader import publishing_api_type


class RuntimePublisher:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, object], str]] = []

    def emit(self, envelope: dict[str, object], /, *, channel: str) -> None:
        self.calls.append((dict(envelope), channel))


def test_multiple_updates_publish_in_order() -> None:
    publisher = RuntimePublisher()
    api = publishing_api_type()(publisher)
    api.put_item("client-a", "x", "1")
    api.put_item("client-a", "x", "2")
    assert [call[0]["value"] for call in publisher.calls] == ["1", "2"]


def test_clients_remain_isolated() -> None:
    publisher = RuntimePublisher()
    api = publishing_api_type()(publisher)
    api.put_item("client-a", "x", "A")
    api.put_item("client-b", "x", "B")
    assert api.get_item("client-a", "x").body["value"] == "A"
    assert api.get_item("client-b", "x").body["value"] == "B"


def test_reads_do_not_publish() -> None:
    publisher = RuntimePublisher()
    api = publishing_api_type()(publisher)
    api.put_item("client-a", "x", "1")
    publisher.calls.clear()
    api.get_item("client-a", "x")
    assert publisher.calls == []


def test_event_payload_is_fresh_per_write() -> None:
    publisher = RuntimePublisher()
    api = publishing_api_type()(publisher)
    api.put_item("client-a", "x", "1")
    first = publisher.calls[0][0]
    api.put_item("client-a", "y", "2")
    second = publisher.calls[1][0]
    assert first == {"type": "item.updated", "client_id": "client-a", "key": "x", "value": "1"}
    assert second == {"type": "item.updated", "client_id": "client-a", "key": "y", "value": "2"}
