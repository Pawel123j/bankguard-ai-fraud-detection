"""Authentication: password hashing, JWT issuing and the analyst dependency.

Replaces the previous demo login, which compared a hardcoded email/password
pair and handed back the constant string ``demo-bankguard-session`` — a token
that no endpoint ever checked. Every ``/api`` route below now depends on
:func:`get_current_analyst`, so the token has to be real and has to verify.

Configuration comes from the environment. There is deliberately **no fallback
secret**: a signing key baked into source is public the moment the repository
is, and an application that starts anyway would sign tokens anyone could forge.
Missing configuration fails loudly at import time instead.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models
from app.database import get_db

ALGORITHM = "HS256"

#: How long an analyst's session lasts. Short by fintech convention — an
#: analyst console is exactly the kind of screen that gets left open.
ACCESS_TOKEN_TTL = timedelta(
    minutes=int(os.getenv("BANKGUARD_TOKEN_TTL_MINUTES", "30"))
)

_MISSING_SECRET_MESSAGE = (
    "BANKGUARD_JWT_SECRET is not set. Generate one with\n"
    "    python -c 'import secrets; print(secrets.token_urlsafe(48))'\n"
    "and export it before starting the API. There is no default: a hardcoded "
    "signing key would let anyone who can read this repository mint valid "
    "analyst tokens."
)


def get_jwt_secret() -> str:
    """Return the signing secret, or refuse to continue without one."""
    secret = os.getenv("BANKGUARD_JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError(_MISSING_SECRET_MESSAGE)
    return secret


def hash_password(plain: str) -> str:
    """Hash a password with bcrypt (per-password salt is generated for us)."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a password against its bcrypt hash.

    bcrypt's comparison is constant-time, so a wrong password costs the same as
    a right one and cannot be distinguished by timing.
    """
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed hash in the database — treat as a failed login rather than
        # a 500, but never as a success.
        return False


def create_access_token(*, subject: str, full_name: str) -> tuple[str, int]:
    """Issue a signed token for an analyst. Returns (token, ttl_seconds)."""
    now = datetime.now(UTC)
    expires_at = now + ACCESS_TOKEN_TTL
    payload = {
        "sub": subject,
        "name": full_name,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, get_jwt_secret(), algorithm=ALGORITHM)
    return token, int(ACCESS_TOKEN_TTL.total_seconds())


_bearer = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_analyst(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.Analyst:
    """Resolve the analyst behind the bearer token, or reject the request.

    Every failure mode returns the same 401 with the same body. Distinguishing
    "no such analyst" from "wrong signature" from "expired" would tell an
    attacker which accounts exist.
    """
    if credentials is None or not credentials.credentials:
        raise _UNAUTHORIZED

    try:
        payload = jwt.decode(
            credentials.credentials, get_jwt_secret(), algorithms=[ALGORITHM]
        )
    except jwt.PyJWTError:
        raise _UNAUTHORIZED from None

    email = payload.get("sub")
    if not email:
        raise _UNAUTHORIZED

    analyst = db.query(models.Analyst).filter(models.Analyst.email == email).first()
    if analyst is None or not analyst.is_active:
        raise _UNAUTHORIZED

    return analyst


WRITER_ROLES = frozenset({"analyst"})


def require_writer(analyst: models.Analyst = Depends(get_current_analyst)) -> models.Analyst:
    """Zmiany danych (import, nowe transakcje, decyzje w sprawach) tylko dla roli analyst (BG-01)."""
    if analyst.role not in WRITER_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Read-only account")
    return analyst
