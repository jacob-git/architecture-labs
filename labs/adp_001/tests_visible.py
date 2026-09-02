from __future__ import annotations

from labs.adp_001.candidate_loader import rate_limited_api_type


class Clock:
    def __init__(self, value: float = 0.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def _api(clock: Clock):
    return rate_limited_api_type()(clock)


def test_ten_requests_allowed_and_eleventh_rejected() -> None:
    clock = Clock()
    api = _api(clock)
    for _ in range(10):
        assert api.health("client-a").status == 200
    assert api.health("client-a").status == 429


def test_existing_api_behavior_is_preserved_for_allowed_requests() -> None:
    clock = Clock()
    api = _api(clock)
    assert api.put_item("client-a", "x", "1").status == 200
    response = api.get_item("client-a", "x")
    assert response.status == 200
    assert response.body == {"key": "x", "value": "1"}
