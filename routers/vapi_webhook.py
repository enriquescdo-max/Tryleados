"""
LeadOS Vapi Webhook Router
Handles all inbound Vapi webhook events.
POSTs to /webhook/vapi are dispatched by message type:

  - end-of-call-report  -> parse transcript -> push to HubSpot -> save to Supabase
  - call-start          -> log
  - status-update       -> log
  - tool-calls          -> reserved for future function-calling tools

Vapi Server URL (set in LeadOS Intake assistant Advanced tab):
  https://tryleados-production.up.railway.app/webhook/vapi
"""

import os
import re
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, BackgroundTasks

log = logging.getLogger("LeadOS.VapiWebhook")
router = APIRouter(prefix="/webhook", tags=["vapi-webhook"])

HUBSPOT_KEY = os.getenv("HUBSPOT_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_KEY", "")
TRANSFER_PHONE = os.getenv("TRANSFER_PHONE", "+16028321135")


# ------------------------------------------------------------------ #
#  TRANSCRIPT PARSER                                                   #
# ------------------------------------------------------------------ #

def _extract(transcript: str, patterns: list) -> str:
    for pat in patterns:
        m = re.search(pat, transcript, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def parse_intake(transcript: str) -> dict:
    if not transcript:
        return {}

    name = _extract(transcript, [
        r"(?:my name is|name\'s|i\'m|this is)\s+([A-Z][a-z]+(?: [A-Z][a-z]+)+)",
        r"([A-Z][a-z]+ [A-Z][a-z]+)(?=,| here| speaking)",
    ])

    phone_raw = _extract(transcript, [
        r"(\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4})",
    ])
    phone = ""
    if phone_raw:
        digits = re.sub(r"[^\d]", "", phone_raw)
        if len(digits) == 10:
            phone = f"+1{digits}"
        elif len(digits) == 11 and digits.startswith("1"):
            phone = f"+{digits}"

    email = _extract(transcript, [
        r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    ])

    address = _extract(transcript, [
        r"(?:address|live at|located at)\s+(.{10,80}(?:TX|Texas|\d{5}))",
        r"(\d+ [A-Z][a-zA-Z\s]{3,40}(?:St|Ave|Blvd|Dr|Ln|Rd|Way|Ct|Pl)[.,\s]*(?:TX|Texas)?\s*\d{5}?)",
    ])

    zip_code = _extract(transcript, [
        r"(?:zip|postal)[^\d]*(\d{5})",
        r"\b(7[5-9]\d{3}|7[0-4]\d{3})\b",
    ])

    t = transcript.lower()
    ins_type = "both" if "both" in t else ("home" if "home" in t or "homeowner" in t else "auto")

    if "transfer" in t or "connecting" in t or "hold for" in t:
        score = 80
    elif "call you back" in t or "15 minute" in t:
        score = 60
    else:
        score = 35

    return {
        "raw_name": name,
        "phone": phone,
        "email": email,
        "address": address,
        "zip_code": zip_code,
        "insurance_type": ins_type,
        "urgency_score": score,
    }


# ------------------------------------------------------------------ #
#  SUPABASE LOGGER                                                     #
# ------------------------------------------------------------------ #

async def _save_supabase(record: dict):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        import httpx
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/vapi_calls",
                headers=headers,
                json=record,
            )
            if resp.status_code not in (200, 201):
                log.warning(f"Supabase vapi_calls: {resp.status_code} {resp.text[:200]}")
    except Exception as exc:
        log.error(f"Supabase error: {exc}")


# ------------------------------------------------------------------ #
#  MAIN WEBHOOK ENDPOINT                                               #
# ------------------------------------------------------------------ #

@router.post("/vapi")
async def vapi_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Single endpoint for ALL Vapi server events.
    Vapi wraps payloads in: { "message": { "type": "...", ... } }
    """
    try:
        payload = await request.json()
    except Exception:
        log.warning("Vapi webhook: invalid JSON body")
        return {"received": False}

    msg = payload.get("message", payload)
    msg_type = msg.get("type", "unknown")
    log.info(f"Vapi event: {msg_type}")

    if msg_type in ("end-of-call-report", "call-end"):
        background_tasks.add_task(_on_call_end, msg)
        return {"received": True, "action": "processing"}

    if msg_type == "call-start":
        log.info(f"Call started: {msg.get('call', {}).get('id', '')}")
        return {"received": True}

    if msg_type == "status-update":
        log.info(f"Status: {msg.get('status')} call={msg.get('call', {}).get('id', '')}")
        return {"received": True}

    if msg_type == "tool-calls":
        return {"results": []}

    if msg_type == "transfer-destination-request":
        return {
            "destination": {
                "type": "number",
                "number": TRANSFER_PHONE,
                "message": "Connecting you to Enrique now, please hold.",
            }
        }

    return {"received": True, "type": msg_type}


# ------------------------------------------------------------------ #
#  CALL-END HANDLER                                                    #
# ------------------------------------------------------------------ #

async def _on_call_end(msg: dict):
    call         = msg.get("call", msg)
    call_id      = call.get("id", "")
    transcript   = msg.get("transcript", "") or call.get("transcript", "")
    recording    = msg.get("recordingUrl", "") or call.get("recordingUrl", "")
    duration     = msg.get("durationSeconds", 0) or call.get("durationSeconds", 0)
    ended_reason = msg.get("endedReason", "") or call.get("endedReason", "")
    caller_phone = call.get("customer", {}).get("number", "") or call.get("phoneNumber", "")

    log.info(f"call-end: id={call_id} duration={duration}s reason={ended_reason}")

    intake = parse_intake(transcript)
    if not intake.get("phone") and caller_phone:
        intake["phone"] = caller_phone

    transferred = (
        "transfer" in (ended_reason or "").lower()
        or intake.get("urgency_score", 0) >= 75
    )

    lead = {
        **intake,
        "call_id": call_id,
        "recording_url": recording,
        "call_duration_seconds": int(duration or 0),
        "ended_reason": ended_reason,
        "transferred": transferred,
        "raw_contact": intake.get("phone") or caller_phone,
        "location": intake.get("address") or intake.get("zip_code", ""),
        "life_event": "insurance_inquiry",
        "outreach_message": "",
        "enrichment_reasoning": (
            f"Inbound Vapi call {call_id}. "
            f"Duration: {duration}s. Ended: {ended_reason}."
        ),
        "carrier_recommendation": "We Insure",
        "source": "vapi_inbound",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Push to HubSpot
    if HUBSPOT_KEY:
        try:
            from services.hubspot import push_lead_to_hubspot
            contact_id = await push_lead_to_hubspot(lead)
            if contact_id:
                lead["hubspot_contact_id"] = contact_id
                log.info(f"HubSpot contact created: {contact_id}")
        except Exception as exc:
            log.error(f"HubSpot push failed: {exc}")
    else:
        log.warning("HUBSPOT_API_KEY not set — skipping HubSpot push")

    # Save to Supabase
    await _save_supabase({
        "call_id":            call_id,
        "caller_phone":       intake.get("phone") or caller_phone,
        "caller_name":        intake.get("raw_name", ""),
        "caller_email":       intake.get("email", ""),
        "caller_address":     intake.get("address", ""),
        "zip_code":           intake.get("zip_code", ""),
        "insurance_type":     intake.get("insurance_type", "auto"),
        "urgency_score":      intake.get("urgency_score", 0),
        "transferred":        transferred,
        "ended_reason":       ended_reason,
        "duration_seconds":   int(duration or 0),
        "recording_url":      recording,
        "transcript":         (transcript or "")[:8000],
        "hubspot_contact_id": lead.get("hubspot_contact_id", ""),
        "created_at":         datetime.now(timezone.utc).isoformat(),
    })

    log.info(
        f"call-end complete: id={call_id} "
        f"transferred={transferred} "
        f"hubspot={lead.get('hubspot_contact_id', 'none')}"
    )
