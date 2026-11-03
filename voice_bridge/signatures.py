"""Standard Webhooks signature check used by the xAI realtime.call.incoming event."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time


def signing_key(secret: str) -> bytes:
    raw = secret[6:] if secret.startswith("whsec_") else secret
    try:
        decoded = base64.b64decode(raw, validate=True)
        if decoded:
            return decoded
    except Exception:
        pass
    return raw.encode("utf-8")


def expected_signature(secret: str, webhook_id: str, timestamp: str, body: bytes) -> str:
    signed = f"{webhook_id}.{timestamp}.".encode("utf-8") + body
    digest = hmac.new(signing_key(secret), signed, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def verify_webhook(secret: str | None, headers: dict, body: bytes, *, now: int | None = None, tolerance: int = 300) -> bool:
    if not secret:
        return False
    webhook_id = headers.get("webhook-id") or headers.get("webhook_id")
    timestamp = headers.get("webhook-timestamp") or headers.get("webhook_timestamp")
    signature = headers.get("webhook-signature") or headers.get("webhook_signature")
    if not webhook_id or not timestamp or not signature:
        return False
    try:
        stamp = int(timestamp)
    except ValueError:
        return False
    current = int(time.time() if now is None else now)
    if abs(current - stamp) > tolerance:
        return False
    expected = expected_signature(secret, webhook_id, str(timestamp), body)
    for part in signature.split():
        version, _, value = part.partition(",")
        if version == "v1" and hmac.compare_digest(expected, value):
            return True
    return False
