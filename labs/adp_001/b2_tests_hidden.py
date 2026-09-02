from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from labs.adp_001.b2_baseline import TinyApi
from labs.adp_001.b2_candidate_loader import cached_api_type


class Clock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def _api(clock: Clock, **kwargs):
    return cached_api_type()(clock, **kwargs)


def test_clients_are_isolated() -> None:
    clock = Clock()
    api = _api(clock)
    api.put_item("client-a", "x", "A")
    api.put_item("client-b", "x", "B")
    assert api.get_item("client-a", "x").body["value"] == "A"
    assert api.get_item("client-b", "x").body["value"] == "B"


def test_404_is_not_sticky_after_later_write() -> None:
    clock = Clock()
    api = _api(clock)
    assert api.get_item("client-a", "x").status == 404
    api.put_item("client-a", "x", "1")
    response = api.get_item("client-a", "x")
    assert response.status == 200
    assert response.body["value"] == "1"


def test_cached_response_cannot_be_mutated_by_caller() -> None:
    clock = Clock()
    api = _api(clock)
    api.put_item("client-a", "x", "1")
    response = api.get_item("client-a", "x")
    response.body["value"] = "tampered"
    fresh = api.get_item("client-a", "x")
    assert fresh.body["value"] == "1"


def test_cache_capacity_is_bounded_and_evicts_lru(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    original = TinyApi.get_item

    def tracked_get(self, client_id: str, key: str):
        calls.append((client_id, key))
        return original(self, client_id, key)

    monkeypatch.setattr(TinyApi, "get_item", tracked_get)
    clock = Clock()
    api = _api(clock, max_entries=4)
    for index in range(5):
        key = f"k{index}"
        api.put_item("client-a", key, str(index))
        assert api.get_item("client-a", key).status == 200

    calls.clear()
    assert api.get_item("client-a", "k0").status == 200
    assert calls == [("client-a", "k0")], "least recently used entry should have been evicted"


def test_concurrent_reads_are_safe() -> None:
    clock = Clock()
    api = _api(clock)
    api.put_item("client-a", "x", "1")
    with ThreadPoolExecutor(max_workers=20) as pool:
        responses = list(pool.map(lambda _: api.get_item("client-a", "x"), range(100)))
    assert all(response.status == 200 for response in responses)
    assert all(response.body == {"key": "x", "value": "1"} for response in responses)


def test_exact_ttl_boundary_is_expired(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []
    original = TinyApi.get_item

    def tracked_get(self, client_id: str, key: str):
        calls.append((client_id, key))
        return original(self, client_id, key)

    monkeypatch.setattr(TinyApi, "get_item", tracked_get)
    clock = Clock()
    api = _api(clock, ttl_seconds=30)
    api.put_item("client-a", "x", "1")
    assert api.get_item("client-a", "x").status == 200
    calls.clear()
    clock.value = 30.0
    assert api.get_item("client-a", "x").status == 200
    assert calls == [("client-a", "x")], "entry must be expired at the exact TTL boundary"
