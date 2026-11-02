"""Pure call planning: allowlist, caller id, intake, and transfer order."""

from __future__ import annotations

import os
import re

from voice_bridge.script import session_update

_PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")


def digits(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def national(value: str | None) -> str:
    raw = digits(value)
    if len(raw) == 11 and raw.startswith("1"):
        return raw[1:]
    return raw


def same_number(left: str | None, right: str | None) -> bool:
    a, b = national(left), national(right)
    return len(a) >= 10 and a == b


def test_mode_enabled() -> bool:
    return os.getenv("VOICE_TEST_MODE", "true").strip().lower() not in {"0", "false", "no", "off"}


def allowlist() -> list[str]:
    return [part.strip() for part in os.getenv("VOICE_ALLOWLIST", "").split(",") if part.strip()]


def caller_allowed(caller: str | None) -> bool:
    if not test_mode_enabled():
        return True
    listed = allowlist()
    if not listed:
        return False
    return any(same_number(caller, item) for item in listed)


def extract_caller(event: dict) -> str:
    headers = (event.get("data") or {}).get("sip_headers") or []
    for header in headers:
        if str(header.get("name", "")).lower() == "from":
            value = header.get("value") or ""
            match = _PHONE.search(value)
            return match.group(0) if match else value
    return ""


def call_id_of(event: dict) -> str:
    return str((event.get("data") or {}).get("call_id") or "")


def build_session(call_id: str) -> dict:
    return {
        "call_id": call_id,
        "url": f"wss://api.x.ai/v1/realtime?call_id={call_id}",
        "model": os.getenv("XAI_VOICE_MODEL", "grok-voice-3.0"),
        "session_update": session_update(),
        "response_create": {"type": "response.create"},
    }


def refer_url(call_id: str) -> str:
    base = os.getenv("XAI_API_BASE", "https://api.x.ai").rstrip("/")
    return f"{base}/v1/realtime/calls/{call_id}/refer"


def hangup_url(call_id: str) -> str:
    base = os.getenv("XAI_API_BASE", "https://api.x.ai").rstrip("/")
    return f"{base}/v1/realtime/calls/{call_id}/hangup"


async def transfer_to_owner(call_id: str, summary: str, sms, refer) -> dict:
    """Text the owner first. Transfer even if the text fails. That second case is a blind transfer."""
    sms_sent = False
    try:
        sms_sent = bool(await sms(summary))
    except Exception:
        sms_sent = False
    owner = os.getenv("OWNER_PHONE", "")
    target = f"tel:{owner}" if owner else ""
    await refer(call_id, target)
    return {
        "sms_sent": sms_sent,
        "transfer": "summary" if sms_sent else "blind",
        "target_uri": target,
    }
