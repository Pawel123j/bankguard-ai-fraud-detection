from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.login_throttle import limit_login
from app.security import (
    create_access_token,
    get_current_analyst,
    verify_password_or_dummy,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    analyst: str


class AnalystResponse(BaseModel):
    email: EmailStr
    analyst: str


@router.post("/login", response_model=LoginResponse, dependencies=[Depends(limit_login)])
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Exchange analyst credentials for a signed, expiring access token."""
    analyst = (
        db.query(models.Analyst)
        .filter(models.Analyst.email == payload.email.lower())
        .first()
    )

    # One message and one status code for every failure: unknown address,
    # wrong password and disabled account must be indistinguishable, or the
    # endpoint becomes a way to enumerate valid analyst accounts. The password
    # is checked BEFORE the account state is looked at, so that every branch
    # pays for exactly one bcrypt comparison and timing does not tell them apart.
    password_ok = verify_password_or_dummy(
        payload.password, analyst.password_hash if analyst else None
    )
    if analyst is None or not analyst.is_active or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token, expires_in = create_access_token(
        subject=analyst.email, full_name=analyst.full_name
    )
    return LoginResponse(
        access_token=token, expires_in=expires_in, analyst=analyst.full_name
    )


@router.get("/me", response_model=AnalystResponse)
def me(analyst: models.Analyst = Depends(get_current_analyst)) -> AnalystResponse:
    """Who the presented token belongs to — used by the frontend on load."""
    return AnalystResponse(email=analyst.email, analyst=analyst.full_name)
