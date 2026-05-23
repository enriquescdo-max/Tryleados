"""LeadOS API — stripped to essentials for Railway stability"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LeadOS")

app = FastAPI(title="LeadOS", version="3.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
try:
    from routers.carrier_scorer import router as carrier_scorer_router
    app.include_router(carrier_scorer_router)
    log.info("carrier_scorer loaded")
except Exception as e:
    log.warning(f"carrier_scorer failed: {e}")

try:
    from routers.campaigns import router as campaigns_router
    app.include_router(campaigns_router)
    log.info("campaigns loaded")
except Exception as e:
    log.warning(f"campaigns failed: {e}")

try:
    from routers.leads import router as leads_router


# ── Vapi Webhook (inbound call events -> HubSpot + Supabase) ─────────────────
import re
from datetime import datetime, timezone
from fastapi import BackgroundTasks

_HUBSPOT_KEY = os.getenv("HUBSPOT_API_KEY", "")
_SUPABASE_URL = os.getenv("SUPABASE_URL", "")
_SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_KEY", "")
_TRANSFER_PHONE = os.getenv("TRANSFER_PHONE", "+16028321135")


def _parse_intake(transcript):
    if not transcript:
        return {}
    t = transcript.lower()
    phone_raw = ""
    pm = re.search(r"(\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4})", transcript)
    if pm:
        digits = re.sub("[^\d]", "", pm.group(1))
        phone_raw = ("+1" + digits) if len(digits) == 10 else ("+" + digits if len(digits) == 11 else "")
    em = re.search(r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})", transcript)
    email = em.group(1) if em else ""
    zm = re.search(r"(?:zip|postal)[^\d]*(\d{5})", transcript, re.IGNORECASE)
    zip_code = zm.group(1) if zm else ""
    ins_type = "both" if "both" in t else ("home" if "home" in t or "homeowner" in t else "auto")
    if "transfer" in t or "connecting" in t or "hold for" in t:
        score = 80
    elif "call you back" in t or "15 minute" in t:
        score = 60
    else:
        score = 35
    return {"phone": phone_raw, "email": email, "zip_code": zip_code, "insurance_type": ins_type, "urgency_score": score}


async def _push_hubspot(lead):
    if not _HUBSPOT_KEY:
        return None
    try:
        from services.hubspot import push_lead_to_hubspot
        return await push_lead_to_hubspot(lead)
    except Exception as exc:
        log.error("HubSpot push failed: %s", exc)
        return None


async def _save_vapi_call(record):
    if not _SUPABASE_URL or not _SUPABASE_KEY:
        return
    try:
        import httpx
        headers = {"apikey": _SUPABASE_KEY, "Authorization": "Bearer " + _SUPABASE_KEY, "Content-Type": "application/json", "Prefer": "return=minimal"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(_SUPABASE_URL + "/rest/v1/vapi_calls", headers=headers, json=record)
            if resp.status_code not in (200, 201):
                log.warning("Supabase vapi_calls: %s", resp.status_code)
    except Exception as exc:
        log.error("Supabase error: %s", exc)


async def _on_call_end(msg):
    from fastapi import Request as _R
    call = msg.get("call", msg)
    call_id = call.get("id", "")
    transcript = msg.get("transcript", "") or call.get("transcript", "")
    recording = msg.get("recordingUrl", "") or call.get("recordingUrl", "")
    duration = msg.get("durationSeconds", 0) or call.get("durationSeconds", 0)
    ended_reason = msg.get("endedReason", "") or call.get("endedReason", "")
    caller_phone = call.get("customer", {}).get("number", "") or call.get("phoneNumber", "")
    log.info("Vapi call-end: id=%s duration=%ss reason=%s", call_id, duration, ended_reason)
    intake = _parse_intake(transcript)
    if not intake.get("phone") and caller_phone:
        intake["phone"] = caller_phone
    transferred = "transfer" in (ended_reason or "").lower() or intake.get("urgency_score", 0) >= 75
    lead = {
        **intake,
        "call_id": call_id, "recording_url": recording, "call_duration_seconds": int(duration or 0),
        "ended_reason": ended_reason, "transferred": transferred, "raw_contact": intake.get("phone") or caller_phone,
        "location": intake.get("zip_code", ""), "life_event": "insurance_inquiry", "outreach_message": "",
        "enrichment_reasoning": "Inbound Vapi call " + call_id + ". Duration: " + str(duration) + "s.",
        "carrier_recommendation": "We Insure", "source": "vapi_inbound",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    contact_id = await _push_hubspot(lead)
    if contact_id:
        lead["hubspot_contact_id"] = contact_id
        log.info("HubSpot contact: %s", contact_id)
    await _save_vapi_call({
        "call_id": call_id, "caller_phone": intake.get("phone") or caller_phone,
        "caller_name": intake.get("raw_name", ""), "caller_email": intake.get("email", ""),
        "zip_code": intake.get("zip_code", ""), "insurance_type": intake.get("insurance_type", "auto"),
        "urgency_score": intake.get("urgency_score", 0), "transferred": transferred,
        "ended_reason": ended_reason, "duration_seconds": int(duration or 0), "recording_url": recording,
        "transcript": (transcript or "")[:8000], "hubspot_contact_id": lead.get("hubspot_contact_id", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    log.info("Vapi call-end done: id=%s transferred=%s hubspot=%s", call_id, transferred, lead.get("hubspot_contact_id", "none"))


@app.post("/webhook/vapi", tags=["vapi-webhook"])
async def vapi_webhook(request: Request, background_tasks: BackgroundTasks):
    """Single endpoint for all Vapi server events (call-end -> HubSpot + Supabase)."""
    try:
        payload = await request.json()
    except Exception:
        return {"received": False}
    msg = payload.get("message", payload)
    msg_type = msg.get("type", "unknown")
    log.info("Vapi event: %s", msg_type)
    if msg_type in ("end-of-call-report", "call-end"):
        background_tasks.add_task(_on_call_end, msg)
        return {"received": True, "action": "processing"}
    if msg_type in ("call-start", "status-update"):
        return {"received": True}
    if msg_type == "tool-calls":
        return {"results": []}
    if msg_type == "transfer-destination-request":
        return {"destination": {"type": "number", "number": _TRANSFER_PHONE, "message": "Connecting you to Enrique now, please hold."}}
    return {"received": True, "type": msg_type}

log.info("=== /webhook/vapi registered ===")
