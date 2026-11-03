"""Shared-secret checks for inbound webhooks. Missing secret fails closed."""

from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request

from core.owner_auth import bearer_token


def verify_shared_secret(presented: str | None, expected: str | None) -> bool:
    if not presented or not expected:
        return False
    return hmac.compare_digest(presented.strip().encode("utf-8"), expected.strip().encode("utf-8"))


def require_vapi_secret(request: Request) -> None:
    expected = os.getenv("VAPI_WEBHOOK_SECRET", "")
    presented = request.headers.get("x-vapi-secret")
    if not presented:
        presented = bearer_token(request.headers.get("authorization"))
        # A Vapi shared secret is not an owner session. Only accept the bearer
        # form when it matches the webhook secret, which verify_shared_secret does.
    if not verify_shared_secret(presented, expected):
        raise HTTPException(status_code=401, detail="Invalid Vapi webhook signature.")


def require_voice_bridge_secret(request: Request) -> None:
    expected = os.getenv("VOICE_BRIDGE_WEBHOOK_SECRET", "")
    presented = request.headers.get("x-voice-bridge-secret")
    if not verify_shared_secret(presented, expected):
        raise HTTPException(status_code=401, detail="Invalid voice bridge signature.")
