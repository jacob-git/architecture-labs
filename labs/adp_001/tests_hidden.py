from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from labs.adp_001.reference_solution import RateLimitedApi


class Clock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def test_clients_are_isolated() -> None:
    clock = Clock()
    api = RateLimitedApi(clock)
    for _ in range(10):
        assert api.health("client-a").status == 200
    assert api.health("client-a").status == 429
    assert api.health("client-b").status == 200


def test_window_reset_restores_capacity() -> None:
    clock = Clock()
    api = RateLimitedApi(clock)
    for _ in range(10):
        assert api.health("client-a").status == 200
    assert api.health("client-a").status == 429
    clock.value = 60.0
    assert api.health("client-a").status == 200


def test_legacy_error_behavior_survives_rate_limit_wrapper() -> None:
    clock = Clock()
    api = RateLimitedApi(clock)
    response = api.get_item("client-a", "missing")
    assert response.status == 404
    assert response.body == {"error": "not_found"}


def test_concurrent_requests_cannot_bypass_limit() -> None:
    clock = Clock()
    api = RateLimitedApi(clock)
    with ThreadPoolExecutor(max_workers=20) as pool:
        statuses = list(pool.map(lambda _: api.health("client-a").status, range(20)))
    assert statuses.count(200) == 10
    assert statuses.count(429) == 10
