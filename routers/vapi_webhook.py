"""
LeadOS Vapi Webhook Router
Single endpoint for all Vapi server events.
Vapi Server URL: https://tryleados-production.up.railway.app/webhook/vapi
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


def _first(transcript, patterns):
    for pat in patterns:
        m = re.search(pat, transcript, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def parse_intake(transcript):
    if not transcript:
        return {}

    name = _first(transcript, [
        "(?:my name is|this is|speaking)\\s+([A-Z][a-z]+ [A-Z][a-z]+)",
        "([A-Z][a-z]+ [A-Z][a-z]+)(?=,| here| speaking)",
    ])

    phone_raw = _first(transcript, [
        "(\\(?\\d{3}\\)?[\\s.\\-]\\d{3}[\\s.\\-]\\d{4})",
    ])
    phone = ""
    if phone_raw:
        digits = re.sub("[^\\d]", "", phone_raw)
        if len(digits) == 10:
            phone = "+1" + digits
        elif len(digits) == 11 and digits.startswith("1"):
            phone = "+" + digits

    email = _first(transcript, [
        "([a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,})",
    ])

    zip_code = _first(transcript, [
        "(?:zip|postal)[^\\d]*(\\d{5})",
        "\\b(7[5-9]\\d{3}|7[0-4]\\d{3})\\b",
    ])

    address = _first(transcript, [
        "(?:address|live at|located at)\\s+(.{10,80}(?:TX|Texas|\\d{5}))",
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


async def _save_supabase(record):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        import httpx
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                SUPABASE_URL + "/rest/v1/vapi_calls",
                headers=headers,
                json=record,
            )
            if resp.status_code not in (200, 201):
                log.warning("Supabase vapi_calls: %s %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        log.error("Supabase error: %s", exc)


@router.post("/vapi")
async def vapi_webhook(request: Request, background_tasks: BackgroundTasks):
    """Single endpoint for ALL Vapi server events."""
    try:
        payload = await request.json()
    except Exception:
        log.warning("Vapi webhook: invalid JSON")
        return {"received": False}

    msg = payload.get("message", payload)
    msg_type = msg.get("type", "unknown")
    log.info("Vapi event: %s", msg_type)

    if msg_type in ("end-of-call-report", "call-end"):
        background_tasks.add_task(_on_call_end, msg)
        return {"received": True, "action": "processing"}

    if msg_type == "call-start":
        log.info("Call started: %s", msg.get("call", {}).get("id", ""))
        return {"received": True}

    if msg_type == "status-update":
        log.info("Status: %s", msg.get("status"))
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


async def _on_call_end(msg):
    call = msg.get("call", msg)
    call_id = call.get("id", "")
    transcript = msg.get("transcript", "") or call.get("transcript", "")
    recording = msg.get("recordingUrl", "") or call.get("recordingUrl", "")
    duration = msg.get("durationSeconds", 0) or call.get("durationSeconds", 0)
    ended_reason = msg.get("endedReason", "") or call.get("endedReason", "")
    caller_phone = call.get("customer", {}).get("number", "") or call.get("phoneNumber", "")

    log.info("call-end: id=%s duration=%ss reason=%s", call_id, duration, ended_reason)

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
        "enrichment_reasoning": "Inbound Vapi call " + call_id + ". Duration: " + str(duration) + "s. Ended: " + ended_reason + ".",
        "carrier_recommendation": "We Insure",
        "source": "vapi_inbound",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    if HUBSPOT_KEY:
        try:
            from services.hubspot import push_lead_to_hubspot
            contact_id = await push_lead_to_hubspot(lead)
            if contact_id:
                lead["hubspot_contact_id"] = contact_id
                log.info("HubSpot contact created: %s", contact_id)
        except Exception as exc:
            log.error("HubSpot push failed: %s", exc)
    else:
        log.warning("HUBSPOT_API_KEY not set")

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

    log.info("call-end done: id=%s transferred=%s hubspot=%s", call_id, transferred, lead.get("hubspot_contact_id", "none"))
