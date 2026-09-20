"""Shared test fixtures.

The signing secret is set before anything imports ``app.security``, which
refuses to load without one — that refusal is itself covered by a test in
``test_auth.py``.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ["BANKGUARD_DATABASE_URL"] = f"sqlite:///{Path(__file__).with_name('test_bankguard.db')}"
os.environ.setdefault("BANKGUARD_JWT_SECRET", "test-secret-not-used-anywhere-real")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.security import hash_password  # noqa: E402

ANALYST_EMAIL = "analyst@bankguard.ai"
ANALYST_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture()
def client() -> TestClient:
    """A client against a freshly created, empty database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


@pytest.fixture()
def analyst(client: TestClient) -> models.Analyst:
    """An active analyst who can sign in."""
    db = SessionLocal()
    try:
        record = models.Analyst(
            email=ANALYST_EMAIL,
            full_name="Test Analyst",
            password_hash=hash_password(ANALYST_PASSWORD),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


@pytest.fixture()
def auth_headers(client: TestClient, analyst: models.Analyst) -> dict[str, str]:
    """Authorization header carrying a real, freshly issued token."""
    response = client.post(
        "/api/auth/login",
        json={"email": ANALYST_EMAIL, "password": ANALYST_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
