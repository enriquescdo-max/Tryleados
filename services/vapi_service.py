"""
LeadOS Vapi Warm Transfer Service
AI agent pre-qualifies leads → warm transfers to Enrique live.

Flow:
1. LeadOS dials lead via Vapi
2. AI agent (Aria) qualifies: coverage type, ZIP, urgency
3. If qualified → warm transfer to Enrique's phone
4. Enrique picks up with full lead context on screen
"""

import os
import asyncio
import logging
import httpx
from typing import Optional

log = logging.getLogger("LeadOS.Vapi")

VAPI_API_KEY     = os.getenv("VAPI_API_KEY", "")
VAPI_BASE        = "https://api.vapi.ai"
AGENT_PHONE      = os.getenv("VAPI_PHONE_NUMBER_ID", "")  # Your Vapi phone number ID
ENRIQUE_PHONE    = os.getenv("ENRIQUE_PHONE", "+18325551234")  # Your real cell


ARIA_SYSTEM_PROMPT = """You are Aria, a friendly insurance intake specialist for Enrique Saucedo at We Insure in Austin, Texas.

Your job: quickly qualify whether this person needs insurance and transfer them to Enrique.

Qualification script:
1. "Hi, is this {first_name}? I'm Aria calling on behalf of Enrique at We Insure in Austin."
2. "I'm reaching out because it looks like you may be in the market for {policy_type} insurance — is that right?"
3. If yes: "Great! What ZIP code would the coverage be for?"
4. "Have you had any gaps in coverage in the last 12 months?"
5. "Are you looking to get coverage started soon, or is this more exploratory?"

If they say yes to needing coverage: "Perfect — Enrique is available right now. Let me connect you — just stay on the line."
Then call the transfer function.

If they're not interested: "No problem at all! If things change, feel free to call us. Have a great day!"

Keep responses SHORT — 1-2 sentences max. Sound human, not robotic. Don't mention you're an AI unless asked directly."""


async def create_call(lead: dict) -> dict:
    """
    Initiate a Vapi outbound call to a lead.
    Returns the call object with call_id.
    """
    if not VAPI_API_KEY:
        return {"error": "VAPI_API_KEY not set", "status": "skipped"}

    phone = _clean_phone(lead.get("raw_contact") or lead.get("phone") or "")
    if not phone:
        return {"error": "No phone number on lead", "status": "skipped"}

    first_name = (lead.get("raw_name") or "there").split()[0].title()
    policy_type = lead.get("insurance_type") or "insurance"
    location = lead.get("location") or "Austin, TX"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                f"{VAPI_BASE}/call",
                headers={
                    "Authorization": f"Bearer {VAPI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "type": "outboundPhoneCall",
                    "phoneNumberId": AGENT_PHONE,
                    "customer": {
                        "number": phone,
                        "name": first_name,
                    },
                    "assistant": {
                        "transcriber": {
                            "provider": "deepgram",
                            "model": "nova-2",
                            "language": "en-US",
                        },
                        "model": {
                            "provider": "anthropic",
                            "model": "claude-haiku-4-5-20251001",
                            "messages": [
                                {
                                    "role": "system",
                                    "content": ARIA_SYSTEM_PROMPT.format(
                                        first_name=first_name,
                                        policy_type=policy_type,
                                        location=location,
                                    ),
                                }
                            ],
                            "temperature": 0.7,
                        },
                        "voice": {
                            "provider": "11labs",
                            "voiceId": "rachel",
                            "stability": 0.5,
                            "similarityBoost": 0.75,
                        },
                        "firstMessage": f"Hi, is this {first_name}? I'm Aria calling on behalf of Enrique at We Insure in Austin.",
                        "endCallFunctionEnabled": True,
                        "transferCallMessage": f"One moment — let me connect you with Enrique now.",
                        "transferDestinationNumber": ENRIQUE_PHONE,
                    },
                    "metadata": {
                        "lead_id": lead.get("id"),
                        "policy_type": policy_type,
                        "source": lead.get("source"),
                        "leados_lead": True,
                    },
                },
            )

            if res.status_code not in (200, 201):
                log.error(f"Vapi error {res.status_code}: {res.text[:300]}")
                return {"error": f"Vapi returned {res.status_code}: {res.text[:100]}", "status": "failed"}

            data = res.json()
            call_id = data.get("id")
            log.info(f"Vapi call initiated: {call_id} → {phone} ({first_name})")

            return {
                "status": "calling",
                "call_id": call_id,
                "phone": phone,
                "lead_name": first_name,
                "message": f"Aria is calling {first_name} at {phone}. Transfer to your phone when qualified.",
            }

    except Exception as e:
        log.error(f"Vapi create_call error: {e}")
        return {"error": str(e), "status": "failed"}


async def get_call_status(call_id: str) -> dict:
    """Get status of a Vapi call."""
    if not VAPI_API_KEY:
        return {"error": "VAPI_API_KEY not set"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{VAPI_BASE}/call/{call_id}",
                headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
            )
            if res.status_code != 200:
                return {"error": f"Status check failed: {res.status_code}"}
            data = res.json()
            return {
                "call_id": call_id,
                "status": data.get("status"),
                "duration": data.get("endedAt"),
                "transcript": data.get("transcript"),
                "summary": data.get("summary"),
                "transferred": data.get("status") == "transferred",
            }
    except Exception as e:
        return {"error": str(e)}


async def list_calls(limit: int = 20) -> list:
    """List recent Vapi calls."""
    if not VAPI_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{VAPI_BASE}/call",
                headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
                params={"limit": limit},
            )
            return res.json() if res.status_code == 200 else []
    except Exception:
        return []


def _clean_phone(phone: str) -> str:
    """Clean phone number to E.164 format."""
    import re
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return "" if len(digits) < 10 else f"+{digits}"
