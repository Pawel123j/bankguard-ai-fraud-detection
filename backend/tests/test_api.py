"""API smoke tests. Auth-specific behaviour lives in test_auth.py."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint_is_public(client: TestClient):
    """Health must stay reachable without a token — probes do not log in."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_stats_on_an_empty_database(client: TestClient, auth_headers):
    response = client.get("/api/dashboard/stats", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_transactions"] == 0
    assert payload["risk_distribution"] == {
        "LOW": 0,
        "MEDIUM": 0,
        "HIGH": 0,
        "CRITICAL": 0,
    }
