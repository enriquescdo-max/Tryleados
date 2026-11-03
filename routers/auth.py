"""Owner login. One person, credentials only from the environment."""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from core.owner_auth import authenticate, auth_configured, bearer_token, issue_token, verify_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(req: LoginRequest):
    if not auth_configured():
        raise HTTPException(status_code=503, detail="Owner login is not configured.")
    if not authenticate(req.email, req.password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = issue_token(req.email)
    return {
        "token": token,
        "user": {"email": req.email.strip().lower(), "role": "owner"},
        "expires_in": 12 * 3600,
    }


@router.get("/me")
async def me(authorization: str | None = Header(None)):
    payload = verify_token(bearer_token(authorization))
    if not payload:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return {"email": payload["sub"], "role": "owner"}
