"""
Vapi inbound call webhook → HubSpot + Supabase
Receives end-of-call-report from Vapi, extracts intake data, pushes to CRM.
"""
import os
import re
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import httpx
from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["vapi"])

HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY", "")
HUBSPOT_OWNER_ID = os.getenv("HUBSPOT_OWNER_ID", "91195509")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")


def extract_field(transcript: str, patterns: list[str]) -> Optional[str]:
    """Try multiple regex patterns to extract a field from transcript."""
    for pat in patterns:
        m = re.search(pat, transcript, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def parse_intake(transcript: str) -> Dict[str, Any]:
    """Extract name, phone, email, address, zip, insurance type from transcript."""
    return {
        "name": extract_field(transcript, [
            r"(?:my name is|i'?m|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        ]),
        "phone": extract_field(transcript, [
            r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",
            r"phone[:\s]+(\+?1?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
        ]),
        "email": extract_field(transcript, [
            r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            r"email[:\s]+([a-zA-Z0-9._%+-]+\s*at\s*[a-zA-Z0-9.-]+\s*dot\s*[a-zA-Z]{2,})",
        ]),
        "zip": extract_field(transcript, [
            r"\b(7[0-9]{4})\b",
            r"zip[:\s]+(\d{5})",
        ]),
        "address": extract_field(transcript, [
            r"address[:\s]+(\d+\s+[A-Za-z0-9\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd))",
        ]),
        "insurance_type": extract_field(transcript, [
            r"\b(auto and home|both auto and home|home and auto)\b",
            r"\b(auto|car) (?:insurance|policy)?",
            r"\b(home|homeowners?) (?:insurance|policy)?",
        ]),
cat > ~/Documents/Tryleados/routers/vapi_webhook.py << 'EOF'
"""
Vapi inbound call webhook → HubSpot + Supabase
Receives end-of-call-report from Vapi, extracts intake data, pushes to CRM.
"""
import os
import re
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import httpx
from fastapi import APIRouter, Request, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["vapi"])

HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY", "")
HUBSPOT_OWNER_ID = os.getenv("HUBSPOT_OWNER_ID", "91195509")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")


def extract_field(transcript: str, patterns: list[str]) -> Optional[str]:
    """Try multiple regex patterns to extract a field from transcript."""
    for pat in patterns:
        m = re.search(pat, transcript, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def parse_intake(transcript: str) -> Dict[str, Any]:
    """Extract name, phone, email, address, zip, insurance type from transcript."""
    return {
        "name": extract_field(transcript, [
            r"(?:my name is|i'?m|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        ]),
        "phone": extract_field(transcript, [
            r"(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})",
            r"phone[:\s]+(\+?1?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})",
        ]),
        "email": extract_field(transcript, [
            r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            r"email[:\s]+([a-zA-Z0-9._%+-]+\s*at\s*[a-zA-Z0-9.-]+\s*dot\s*[a-zA-Z]{2,})",
        ]),
        "zip": extract_field(transcript, [
            r"\b(7[0-9]{4})\b",
            r"zip[:\s]+(\d{5})",
        ]),
        "address": extract_field(transcript, [
            r"address[:\s]+(\d+\s+[A-Za-z0-9\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|boulevard|blvd))",
        ]),
        "insurance_type": extract_field(transcript, [
            r"\b(auto and home|both auto and home|home and auto)\b",
            r"\b(auto|car) (?:insurance|policy)?",
            r"\b(home|homeowners?) (?:insurance|policy)?",
        ]),
        "transferred": bool(re.search(r"transfer.*enrique|connecting.*enrique", transcript, re.IGNORECASE)),
    }


async def push_to_hubspot(intake: Dict[str, Any], transcript: str, call_id: str) -> Optional[str]:
    """Create or update HubSpot contact. Returns contact ID."""
    if not HUBSPOT_API_KEY or not intake.get("phone"):
        logger.warning("Skipping HubSpot: missing API key or phone")
        return None

    properties = {
        "phone": intake.get("phone", ""),
        "email": intake.get("email", "") or "",
        "hubspot_owner_id": HUBSPOT_OWNER_ID,
        "lifecyclestage": "lead",
        "lead_source": "Vapi Inbound Call",
        "hs_lead_status": "NEW",
    }
    if intake.get("name"):
        parts = intake["name"].split(maxsplit=1)
        properties["firstname"] = parts[0]
        if len(parts) > 1:
            properties["lastname"] = parts[1]
    if intake.get("zip"):
        properties["zip"] = intake["zip"]
    if intake.get("address"):
        properties["address"] = intake["address"]
    if intake.get("insurance_type"):
        properties["insurance_interest"] = intake["insurance_type"]

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.hubapi.com/crm/v3/objects/contacts",
            headers={"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"},
            json={"properties": properties},
        )
        if r.status_code == 409:
            logger.info(f"Contact exists, updating by phone: {intake.get('phone')}")
            search = await client.post(
                "https://api.hubapi.com/crm/v3/objects/contacts/search",
                headers={"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"},
                json={"filterGroups": [{"filters": [{"propertyName": "phone", "operator": "EQ", "value": intake["phone"]}]}]},
            )
            results = search.json().get("results", [])
            if results:
                contact_id = results[0]["id"]
                await client.patch(
                    f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}",
                    headers={"Authorization": f"Bearer {HUBSPOT_API_KEY}", "Content-Type": "application/json"},
                    json={"properties": properties},
                )
                return contact_id
        elif r.status_code in (200, 201):
            return r.json().get("id")
        else:
            logger.error(f"HubSpot error {r.status_code}: {r.text}")
            return None


async def save_to_supabase(payload: dict, intake: dict, hubspot_id: Optional[str]) -> bool:
    """Insert call record into Supabase vapi_calls table."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Skipping Supabase: missing URL or key")
        return False
    call = payload.get("message", {}).get("call", {}) or payload.get("call", {})
    row = {
        "vapi_call_id": call.get("id"),
        "event_type": payload.get("message", {}).get("type", "unknown"),
        "caller_phone": intake.get("phone"),
        "caller_name": intake.get("name"),
        "caller_email": intake.get("email"),
        "caller_address": intake.get("address"),
        "caller_zip": intake.get("zip"),
        "insurance_type": intake.get("insurance_type"),
        "transferred": intake.get("transferred", False),
        "transcript": payload.get("message", {}).get("transcript", "")[:50000],
        "hubspot_contact_id": hubspot_id,
        "raw_payload": payload,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{SUPABASE_URL}/rest/v1/vapi_calls",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=row,
        )
        if r.status_code in (200, 201, 204):
            return True
        logger.error(f"Supabase error {r.status_code}: {r.text}")
        return False


@router.post("/vapi")
async def vapi_webhook(request: Request):
    """Receive Vapi event, route on type."""
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(400, f"Invalid JSON: {e}")

    msg = payload.get("message", {})
    event_type = msg.get("type", "unknown")
    logger.info(f"Vapi webhook: {event_type}")

    if event_type == "end-of-call-report":
        transcript = msg.get("transcript", "") or ""
        intake = parse_intake(transcript)
        logger.info(f"Extracted intake: {intake}")
        hubspot_id = await push_to_hubspot(intake, transcript, msg.get("call", {}).get("id", ""))
        supabase_ok = await save_to_supabase(payload, intake, hubspot_id)
        return {
            "status": "processed",
            "event": event_type,
            "intake": intake,
            "hubspot_contact_id": hubspot_id,
            "supabase_saved": supabase_ok,
        }

    return {"status": "received", "event": event_type}
