"""Authentication tests.

These exist because the previous login was decorative: it compared a hardcoded
pair and returned a constant string that no endpoint ever checked. Each test
below pins down one property that regression would quietly undo.
"""

from __future__ import annotations

import importlib
import os

import jwt
import pytest
from fastapi.testclient import TestClient

from app import models
from app.database import SessionLocal
from app.security import get_jwt_secret, hash_password, verify_password
from tests.conftest import ANALYST_EMAIL, ANALYST_PASSWORD


# --- token issuing ---------------------------------------------------------


def test_login_returns_a_real_signed_token(client: TestClient, analyst):
    response = client.post(
        "/api/auth/login", json={"email": ANALYST_EMAIL, "password": ANALYST_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0

    # It must be a JWT this service can verify — not a constant string.
    claims = jwt.decode(body["access_token"], get_jwt_secret(), algorithms=["HS256"])
    assert claims["sub"] == ANALYST_EMAIL
    assert claims["exp"] > claims["iat"]


def test_token_is_not_a_fixed_string(client: TestClient, analyst):
    """Two logins must not produce an interchangeable credential."""
    payload = {"email": ANALYST_EMAIL, "password": ANALYST_PASSWORD}
    first = client.post("/api/auth/login", json=payload).json()["access_token"]
    second = client.post("/api/auth/login", json=payload).json()["access_token"]

    # Same second, so iat/exp may match; what matters is that it is a signed
    # JWT bound to a subject rather than the old constant.
    assert first.count(".") == 2
    assert first != "demo-bankguard-session"
    assert second != "demo-bankguard-session"


# --- login failures --------------------------------------------------------


@pytest.mark.parametrize(
    "email,password",
    [
        (ANALYST_EMAIL, "wrong-password"),
        ("nobody@bankguard.ai", ANALYST_PASSWORD),
        ("nobody@bankguard.ai", "wrong-password"),
    ],
)
def test_bad_credentials_are_rejected_identically(
    client: TestClient, analyst, email, password
):
    """Unknown account and wrong password must be indistinguishable.

    A different status or message would turn this endpoint into an analyst
    account enumerator.
    """
    response = client.post("/api/auth/login", json={"email": email, "password": password})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_deactivated_analyst_cannot_log_in(client: TestClient, analyst):
    db = SessionLocal()
    try:
        record = db.query(models.Analyst).filter(models.Analyst.email == ANALYST_EMAIL).one()
        record.is_active = False
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/auth/login", json={"email": ANALYST_EMAIL, "password": ANALYST_PASSWORD}
    )
    assert response.status_code == 401


# --- protected routes ------------------------------------------------------


PROTECTED = [
    ("get", "/api/dashboard/stats"),
    ("get", "/api/transactions"),
    ("get", "/api/cases"),
    ("get", "/api/reports/summary"),
    ("get", "/api/auth/me"),
]


@pytest.mark.parametrize("method,path", PROTECTED)
def test_protected_routes_reject_anonymous_requests(client: TestClient, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401, f"{path} answered {response.status_code} without a token"


@pytest.mark.parametrize("method,path", PROTECTED)
def test_protected_routes_accept_a_valid_token(client: TestClient, auth_headers, method, path):
    response = getattr(client, method)(path, headers=auth_headers)
    assert response.status_code == 200, f"{path}: {response.text}"


def test_garbage_token_is_rejected(client: TestClient, analyst):
    response = client.get(
        "/api/dashboard/stats", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401


def test_token_signed_with_another_secret_is_rejected(client: TestClient, analyst):
    """A forged token must not be accepted just because it is well-formed."""
    forged = jwt.encode(
        {"sub": ANALYST_EMAIL, "name": "Attacker", "iat": 0, "exp": 9999999999},
        "some-other-secret",
        algorithm="HS256",
    )
    response = client.get(
        "/api/dashboard/stats", headers={"Authorization": f"Bearer {forged}"}
    )
    assert response.status_code == 401


def test_expired_token_is_rejected(client: TestClient, analyst):
    expired = jwt.encode(
        {"sub": ANALYST_EMAIL, "name": "Test Analyst", "iat": 0, "exp": 1},
        get_jwt_secret(),
        algorithm="HS256",
    )
    response = client.get(
        "/api/dashboard/stats", headers={"Authorization": f"Bearer {expired}"}
    )
    assert response.status_code == 401


def test_token_for_a_deleted_analyst_is_rejected(client: TestClient, auth_headers):
    """A valid signature is not enough — the subject must still exist."""
    db = SessionLocal()
    try:
        db.query(models.Analyst).delete()
        db.commit()
    finally:
        db.close()

    response = client.get("/api/dashboard/stats", headers=auth_headers)
    assert response.status_code == 401


# --- password hashing ------------------------------------------------------


def test_passwords_are_hashed_not_stored():
    hashed = hash_password("hunter2")

    assert hashed != "hunter2"
    assert hashed.startswith("$2")  # bcrypt
    assert verify_password("hunter2", hashed)
    assert not verify_password("hunter3", hashed)


def test_same_password_hashes_differently_each_time():
    """Per-password salt: identical passwords must not share a hash."""
    assert hash_password("hunter2") != hash_password("hunter2")


def test_malformed_hash_fails_closed():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


# --- configuration ---------------------------------------------------------


def test_missing_jwt_secret_is_fatal(monkeypatch):
    """No fallback secret: the app must refuse rather than sign with a default."""
    import app.security as security

    # Zapamiętaj to, co faktycznie jest skonfigurowane — test nie może
    # zakładać konkretnej wartości, bo CI podaje własną.
    original = os.environ["BANKGUARD_JWT_SECRET"]

    monkeypatch.delenv("BANKGUARD_JWT_SECRET", raising=False)
    importlib.reload(security)
    try:
        with pytest.raises(RuntimeError, match="BANKGUARD_JWT_SECRET"):
            security.get_jwt_secret()
    finally:
        # monkeypatch cofnie zmienną, ale nie przeładowanie modułu — musimy
        # przywrócić oba, inaczej kolejne testy dostaną zepsuty moduł.
        monkeypatch.setenv("BANKGUARD_JWT_SECRET", original)
        importlib.reload(security)
