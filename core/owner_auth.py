"""Single-owner session tokens.

The in-memory user table and its default password are gone. The owner email,
password hash, and signing secret come from the environment. Tokens are
HMAC-signed and expire. Nothing about a session is stored in process memory.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time


def auth_configured() -> bool:
    return bool(
        os.getenv("LEADOS_OWNER_EMAIL", "").strip()
        and os.getenv("LEADOS_OWNER_PASSWORD_HASH", "").strip()
        and os.getenv("LEADOS_SESSION_SECRET", "").strip()
    )


def hash_password(password: str, *, salt: bytes | None = None, iterations: int = 600_000) -> str:
    """Hash a password for LEADOS_OWNER_PASSWORD_HASH. Never store the password."""
    import secrets

    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_b64, hash_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(hash_b64.encode("ascii"))
        got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(got, expected)
    except Exception:
        return False


def authenticate(email: str, password: str) -> bool:
    if not auth_configured():
        return False
    owner = os.environ["LEADOS_OWNER_EMAIL"].strip().lower()
    if email.strip().lower() != owner:
        return False
    return verify_password(password, os.environ["LEADOS_OWNER_PASSWORD_HASH"].strip())


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))


def issue_token(email: str, *, ttl_seconds: int = 12 * 3600, now: int | None = None) -> str:
    secret = os.environ["LEADOS_SESSION_SECRET"]
    issued = int(time.time() if now is None else now)
    payload = {
        "sub": email.strip().lower(),
        "role": "owner",
        "iat": issued,
        "exp": issued + ttl_seconds,
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = _b64(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def verify_token(token: str | None, *, now: int | None = None) -> dict | None:
    secret = os.getenv("LEADOS_SESSION_SECRET", "")
    if not token or not secret or token.count(".") != 1:
        return None
    body, sig = token.split(".", 1)
    expected = _b64(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        payload = json.loads(_b64decode(body))
    except Exception:
        return None
    current = int(time.time() if now is None else now)
    if int(payload.get("exp", 0)) < current:
        return None
    if payload.get("role") != "owner":
        return None
    owner = os.getenv("LEADOS_OWNER_EMAIL", "").strip().lower()
    if owner and payload.get("sub") != owner:
        return None
    return payload


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()
