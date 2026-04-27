from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, HTTPException, status


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "demo"
    analyst: str


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    if payload.email != "analyst@bankguard.ai" or payload.password != "demo123":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid demo credentials",
        )

    return LoginResponse(access_token="demo-bankguard-session", analyst="Fraud Analyst")

