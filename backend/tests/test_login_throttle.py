from concurrent.futures import ThreadPoolExecutor

import pytest
from app.login_throttle import LoginThrottle
from fastapi import HTTPException


def test_login_api_limits_attempts_and_ignores_spoofed_forwarding(client):
    payload = {"email": "unknown@example.org", "password": "invalid"}
    for _ in range(10):
        assert client.post("/api/auth/login", json=payload).status_code == 401
    response = client.post("/api/auth/login", json=payload,
                           headers={"X-Forwarded-For": "203.0.113.5"})
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_budgets_expire_without_unbounded_memory():
    now = [1000.0]
    throttle = LoginThrottle(limit=1, window_seconds=10, max_clients=2, clock=lambda: now[0])
    throttle.check("a")
    with pytest.raises(HTTPException) as error:
        throttle.check("a")
    assert error.value.status_code == 429
    now[0] += 11
    throttle.check("a")
    throttle.check("b")
    throttle.check("c")
    assert len(throttle.clients) == 2


def test_parallel_attempts_cannot_exceed_budget():
    throttle = LoginThrottle(limit=3)
    def attempt(_):
        try:
            throttle.check("shared-client")
            return True
        except HTTPException:
            return False
    with ThreadPoolExecutor(max_workers=12) as pool:
        assert sum(pool.map(attempt, range(12))) == 3
