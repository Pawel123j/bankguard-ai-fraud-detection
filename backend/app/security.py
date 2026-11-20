"""Authentication: password hashing, JWT issuing and the analyst dependency.

Replaces the previous demo login, which compared a hardcoded email/password
pair and handed back the constant string ``demo-bankguard-session`` — a token
that no endpoint ever checked. Every ``/api`` route below now depends on
:func:`get_current_analyst`, so the token has to be real and has to verify.

Configuration comes from the environment. There is deliberately **no fallback
secret**: a signing key baked into source is public the moment the repository
is, and an application that starts anyway would sign tokens anyone could forge.
Missing or too-short configuration makes the API refuse to start (see the
``lifespan`` hook in ``app.main``) instead of failing on the first request.
"""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime, timedelta
from functools import lru_cache

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


#: RFC 7518 §3.2: an HS256 key must be at least as long as the hash output.
#: A shorter key can be brute-forced offline from a single captured token.
MIN_SECRET_BYTES = 32

_SHORT_SECRET_MESSAGE = (
    f"BANKGUARD_JWT_SECRET is shorter than {MIN_SECRET_BYTES} bytes. HS256 tokens "
    "signed with a short key can be brute-forced offline. Generate a strong one with\n"
    "    python -c 'import secrets; print(secrets.token_urlsafe(48))'"
)


def get_jwt_secret() -> str:
    """Return the signing secret, or refuse to continue without a strong one."""
    secret = os.getenv("BANKGUARD_JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError(_MISSING_SECRET_MESSAGE)
    if len(secret.encode("utf-8")) < MIN_SECRET_BYTES:
        raise RuntimeError(_SHORT_SECRET_MESSAGE)
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


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    """A bcrypt hash of a random value, built with the same cost as real ones."""
    return hash_password(secrets.token_urlsafe(24))


def verify_password_or_dummy(plain: str, hashed: str | None) -> bool:
    """Like :func:`verify_password`, but spends one bcrypt comparison even when
    there is no stored hash.

    Without this, a login for an unknown address returns after a dictionary
    lookup while a known address pays for a full bcrypt check, so the response
    time reveals which analyst accounts exist even though the status code and
    message are identical.
    """
    if hashed is None:
        verify_password(plain, _dummy_hash())
        return False
    return verify_password(plain, hashed)


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
        # PyJWT checks `exp` only when it is present; require it (and `sub`) so
        # a correctly signed token without an expiry is not accepted forever.
        payload = jwt.decode(
            credentials.credentials,
            get_jwt_secret(),
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
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
