"""Fly.io process. Twilio SIP lands on xAI. xAI posts the incoming call here."""

from __future__ import annotations

import json
import os

from fastapi import FastAPI, HTTPException, Request

from voice_bridge.calls import build_session, caller_allowed, call_id_of, extract_caller, hangup_url, refer_url
from voice_bridge.signatures import verify_webhook

app = FastAPI(title="LeadOS voice bridge", version="1.0")


class BridgeDeps:
    def __init__(self, hangup, start_session, secret: str | None = None):
        self.hangup = hangup
        self.start_session = start_session
        self.secret = secret if secret is not None else os.getenv("XAI_WEBHOOK_SECRET", "")


def _default_deps() -> BridgeDeps:
    async def hangup(call_id: str):
        return {"hangup": hangup_url(call_id)}

    async def start_session(call_id: str, caller: str):
        return build_session(call_id)

    return BridgeDeps(hangup, start_session)


DEPS = _default_deps()


def set_deps(deps: BridgeDeps):
    global DEPS
    DEPS = deps


@app.get("/health")
async def health():
    return {"status": "ok", "test_mode": os.getenv("VOICE_TEST_MODE", "true"), "inbound_only": True}


@app.post("/webhooks/xai")
async def incoming(request: Request):
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    if not verify_webhook(DEPS.secret, headers, body):
        raise HTTPException(status_code=401, detail="Invalid xAI webhook signature.")
    try:
        event = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    if event.get("type") != "realtime.call.incoming":
        return {"ok": True, "ignored": True}
    call_id = call_id_of(event)
    caller = extract_caller(event)
    if not caller_allowed(caller):
        await DEPS.hangup(call_id)
        return {"ok": True, "disposition": "rejected_test_mode"}
    session = await DEPS.start_session(call_id, caller)
    return {"ok": True, "disposition": "accepted", "session": session, "refer_url": refer_url(call_id)}
