"""
auth_routes.py — Signup, login, logout, and current-user endpoints.

Self-hosted email/password authentication, mounted onto the main app via
app.include_router(). Login issues an opaque session token using the Bearer
scheme: the client stores the token and sends it as
`Authorization: Bearer <token>` on subsequent requests.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field

import db
from auth import (
    generate_session_token,
    hash_password,
    hash_token,
    session_expiry,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Bearer-token scheme. auto_error=False lets us return our own 401 wording.
_bearer = HTTPBearer(auto_error=False)


# ---------- Models ----------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)


class UserResponse(BaseModel):
    id: int
    email: str
    tier: str
    created_at: str | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


# ---------- Current-user dependency ----------

def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """Resolve the logged-in user from the Bearer token, or raise 401."""
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    user = db.get_session_user(hash_token(creds.credentials))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return user


# ---------- Routes ----------

@router.post("/signup", status_code=201, response_model=AuthResponse)
def signup(request: SignupRequest) -> AuthResponse:
    email = request.email.strip()
    if db.get_user_by_email(email) is not None:
        raise HTTPException(
            status_code=409,
            detail="An account with that email already exists.",
        )

    user = db.create_user(email, hash_password(request.password))

    token = generate_session_token()
    db.create_session(user["id"], hash_token(token), session_expiry())

    return AuthResponse(token=token, user=UserResponse(**user))


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    user = db.get_user_by_email(request.email.strip())
    if user is None or not verify_password(request.password, user["password_hash"]):
        # Deliberately generic so we don't reveal which accounts exist.
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    token = generate_session_token()
    db.create_session(user["id"], hash_token(token), session_expiry())

    safe_user = {k: user[k] for k in ("id", "email", "tier", "created_at")}
    return AuthResponse(token=token, user=UserResponse(**safe_user))


@router.post("/logout", status_code=204)
def logout(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    # Idempotent: deleting a missing/already-gone session is fine.
    if creds is not None and creds.credentials:
        db.delete_session(hash_token(creds.credentials))


@router.get("/me", response_model=UserResponse)
def me(current_user: dict = Depends(get_current_user)) -> UserResponse:
    return UserResponse(**current_user)

