"""Reject unauthenticated access to lead, outreach, and admin routes.

Webhooks and the login endpoint stay public. Webhook handlers verify their
own signatures and must fail closed when the secret is missing.
"""

from __future__ import annotations

from core.owner_auth import bearer_token, verify_token

_PUBLIC_EXACT = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
    "/api/auth/login",
    "/auth/login",
    "/auth/logout",
    "/billing/webhook",
    "/agents/health",
}


def normalize_path(path: str) -> str:
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return path or "/"


def is_public(path: str) -> bool:
    path = normalize_path(path)
    if path in _PUBLIC_EXACT:
        return True
    if path.startswith("/webhook/") or path.startswith("/api/public/") or path.startswith("/docs"):
        return True
    return False


class OwnerAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path") or "/"
        if scope.get("method") == "OPTIONS" or is_public(path):
            await self.app(scope, receive, send)
            return
        headers = {key.decode("latin1").lower(): value.decode("latin1") for key, value in scope.get("headers") or []}
        if not verify_token(bearer_token(headers.get("authorization"))):
            body = b'{"detail":"Not authenticated."}'
            await send({
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            })
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)
