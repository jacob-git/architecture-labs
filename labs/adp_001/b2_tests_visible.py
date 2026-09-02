from __future__ import annotations

from labs.adp_001.b2_candidate_loader import cached_api_type


class Clock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def _api(clock: Clock):
    return cached_api_type()(clock)


def test_cached_read_preserves_existing_behavior() -> None:
    clock = Clock()
    api = _api(clock)
    assert api.put_item("client-a", "x", "1").status == 200
    first = api.get_item("client-a", "x")
    second = api.get_item("client-a", "x")
    assert first.status == 200
    assert first.body == {"key": "x", "value": "1"}
    assert second.body == first.body


def test_write_invalidates_cached_value() -> None:
    clock = Clock()
    api = _api(clock)
    api.put_item("client-a", "x", "1")
    assert api.get_item("client-a", "x").body["value"] == "1"
    api.put_item("client-a", "x", "2")
    assert api.get_item("client-a", "x").body["value"] == "2"


def test_entry_expires_after_ttl() -> None:
    clock = Clock()
    api = _api(clock)
    api.put_item("client-a", "x", "1")
    assert api.get_item("client-a", "x").status == 200
    clock.value = 30.0
    assert api.get_item("client-a", "x").status == 200
