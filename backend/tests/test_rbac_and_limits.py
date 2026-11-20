"""BG-01 (rola tylko do odczytu, rozliczalność zmian) i BG-02 (limity list)."""

import sqlite3

from app import database, models
from app.database import SessionLocal
from app.security import hash_password
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect

VIEWER_EMAIL = "viewer@example.com"
VIEWER_PASSWORD = "viewer-password-for-tests"
TX = {
    "transaction_id": "TX-RBAC-1", "customer_id": "C-1", "amount": 25000, "currency": "USD",
    "merchant": "Shop", "merchant_category": "electronics", "country": "Nigeria", "city": "Lagos",
    "channel": "ONLINE", "transaction_date": "2026-06-10T02:00:00Z", "is_foreign": True,
    "is_night_transaction": True, "previous_failed_attempts": 4, "device_trust_score": 10,
}


def _viewer_headers(client: TestClient) -> dict[str, str]:
    db = SessionLocal()
    try:
        db.add(models.Analyst(email=VIEWER_EMAIL, full_name="Viewer",
                              password_hash=hash_password(VIEWER_PASSWORD), role="viewer"))
        db.commit()
    finally:
        db.close()
    token = client.post("/api/auth/login", json={"email": VIEWER_EMAIL, "password": VIEWER_PASSWORD})
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


def test_viewer_can_read_but_not_write(client: TestClient, auth_headers):
    created = client.post("/api/transactions", json=TX, headers=auth_headers)
    assert created.status_code == 201
    viewer = _viewer_headers(client)
    assert client.get("/api/transactions", headers=viewer).status_code == 200
    assert client.post("/api/transactions", json={**TX, "transaction_id": "TX-2"}, headers=viewer).status_code == 403
    case_id = client.get("/api/cases", headers=auth_headers).json()[0]["id"]
    assert client.patch(f"/api/cases/{case_id}", json={"status": "RESOLVED"}, headers=viewer).status_code == 403
    upload = client.post("/api/transactions/import", files={"file": ("t.csv", b"a\n1\n")}, headers=viewer)
    assert upload.status_code == 403


def test_case_update_records_the_acting_analyst(client: TestClient, auth_headers, analyst):
    client.post("/api/transactions", json=TX, headers=auth_headers)
    case_id = client.get("/api/cases", headers=auth_headers).json()[0]["id"]
    updated = client.patch(f"/api/cases/{case_id}", json={"status": "INVESTIGATING"}, headers=auth_headers)
    assert updated.status_code == 200
    assert updated.json()["updated_by"] == analyst.email


def test_list_endpoints_are_bounded(client: TestClient, auth_headers):
    assert client.get("/api/transactions?limit=5000", headers=auth_headers).status_code == 422
    assert client.get("/api/cases?limit=0", headers=auth_headers).status_code == 422
    for i in range(3):
        client.post("/api/transactions", json={**TX, "transaction_id": f"TX-L{i}"}, headers=auth_headers)
    page = client.get("/api/transactions?limit=2&offset=1", headers=auth_headers)
    assert len(page.json()) == 2


def test_case_notes_length_is_bounded(client: TestClient, auth_headers):
    client.post("/api/transactions", json=TX, headers=auth_headers)
    case_id = client.get("/api/cases", headers=auth_headers).json()[0]["id"]
    too_long = client.patch(f"/api/cases/{case_id}", json={"notes": "x" * 5001}, headers=auth_headers)
    assert too_long.status_code == 422


def test_existing_database_gets_new_columns(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as legacy:
        legacy.execute("CREATE TABLE analysts (id INTEGER PRIMARY KEY, email VARCHAR(255) NOT NULL, "
                       "full_name VARCHAR(160) NOT NULL, password_hash VARCHAR(255) NOT NULL, "
                       "is_active BOOLEAN NOT NULL, created_at DATETIME NOT NULL)")
        legacy.execute("INSERT INTO analysts VALUES (1, 'a@b.c', 'A', 'x', 1, '2026-01-01')")
    legacy_engine = create_engine(f"sqlite:///{path}")
    monkeypatch.setattr(database, "engine", legacy_engine)
    database.init_db()
    database.init_db()  # idempotentne
    columns = {c["name"] for c in inspect(legacy_engine).get_columns("analysts")}
    assert "role" in columns
    with legacy_engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT role FROM analysts").scalar() == "analyst"
    assert "updated_by" in {c["name"] for c in inspect(legacy_engine).get_columns("fraud_cases")}
