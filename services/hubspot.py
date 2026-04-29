"""
LeadOS HubSpot Sync
Pushes leads to HubSpot CRM as contacts with notes.
Uses only standard HubSpot properties to avoid custom property errors.
"""

import httpx
import os
import time
import logging

log = logging.getLogger("LeadOS.HubSpot")

HUBSPOT_BASE = "https://api.hubapi.com"
HUBSPOT_KEY  = os.getenv("HUBSPOT_API_KEY", "")
OWNER_ID     = os.getenv("HUBSPOT_OWNER_ID", "91195509")


async def push_lead_to_hubspot(lead: dict) -> str:
    """Push a single lead to HubSpot as a contact + note."""
    if not HUBSPOT_KEY:
        log.warning("HUBSPOT_API_KEY not set — skipping HubSpot sync")
        return None

    headers = {
        "Authorization": f"Bearer {HUBSPOT_KEY}",
        "Content-Type": "application/json",
    }

    # Parse name
    full_name = lead.get("raw_name") or lead.get("name") or "Unknown Lead"
    parts = full_name.strip().split()
    first = parts[0] if parts else "Unknown"
    last  = " ".join(parts[1:]) if len(parts) > 1 else "LeadOS"

    # Parse phone
    phone = lead.get("raw_contact") or lead.get("phone") or ""

    # Parse location
    location = lead.get("location") or ""
    city = "Austin"
    state = "TX"
    zip_code = ""
    if "·" in location:
        parts_loc = location.split("·")
        zip_part = parts_loc[0].strip()
        city_state = parts_loc[-1].strip()
        if zip_part.isdigit() and len(zip_part) == 5:
            zip_code = zip_part
        if " " in city_state:
            city_parts = city_state.split()
            city  = " ".join(city_parts[:-1])
            state = city_parts[-1]

    # Build note body
    note_body = (
        f"📋 LeadOS Lead\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Source: {lead.get('source', 'Unknown')}\n"
        f"Insurance Type: {lead.get('insurance_type', 'auto').upper()}\n"
        f"Urgency Score: {lead.get('urgency_score', '?')}/10\n"
        f"Carrier Recommendation: {lead.get('carrier_recommendation', 'TBD')}\n"
        f"Life Event: {lead.get('life_event', 'Unknown')}\n"
        f"ZIP: {zip_code or location}\n\n"
        f"📞 Outreach Script:\n{lead.get('outreach_message', 'See LeadOS for script')}\n\n"
        f"🤖 AI Reasoning:\n{lead.get('enrichment_reasoning', '')[:300]}"
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:

            # 1. Create or update contact
            contact_payload = {
                "properties": {
                    "firstname":       first,
                    "lastname":        last,
                    "phone":           phone,
                    "city":            city,
                    "state":           state,
                    "zip":             zip_code,
                    "hs_lead_status":  "NEW",
                    "hubspot_owner_id": OWNER_ID,
                    "leadsource":      "OTHER",  # Standard HubSpot field
                    "description":     f"LeadOS | {lead.get('insurance_type','auto')} | Score: {lead.get('urgency_score','?')}/10 | {lead.get('source','')}",
                }
            }

            # Try to create contact
            resp = await client.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/contacts",
                headers=headers,
                json=contact_payload,
            )

            # If duplicate (409), search for existing contact
            if resp.status_code == 409 and phone:
                search_resp = await client.post(
                    f"{HUBSPOT_BASE}/crm/v3/objects/contacts/search",
                    headers=headers,
                    json={
                        "filterGroups": [{"filters": [{"propertyName": "phone", "operator": "EQ", "value": phone}]}],
                        "properties": ["id", "firstname", "lastname"],
                    },
                )
                results = search_resp.json().get("results", [])
                if results:
                    contact_id = results[0]["id"]
                    log.info(f"HubSpot: Found existing contact {contact_id} for {first}")
                else:
                    log.warning(f"HubSpot: 409 but no existing contact found for {first}")
                    return None

            elif resp.status_code in (200, 201):
                contact_id = resp.json().get("id")
                log.info(f"HubSpot: Created contact {contact_id} for {first} {last}")

            else:
                log.error(f"HubSpot create contact failed: {resp.status_code} — {resp.text[:200]}")
                return None

            # 2. Create note attached to contact
            note_resp = await client.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/notes",
                headers=headers,
                json={
                    "properties": {
                        "hs_note_body":  note_body,
                        "hs_timestamp":  str(int(time.time() * 1000)),
                    },
                    "associations": [
                        {
                            "to": {"id": contact_id},
                            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}],
                        }
                    ],
                },
            )

            if note_resp.status_code in (200, 201):
                log.info(f"HubSpot: Note created for contact {contact_id}")
            else:
                log.warning(f"HubSpot: Note failed {note_resp.status_code}")

            return contact_id

    except Exception as e:
        log.error(f"HubSpot push_lead error: {e}")
        return None


async def sync_all_leads_to_hubspot() -> dict:
    """Sync ALL leads from Supabase to HubSpot. Call manually to backfill."""
    if not HUBSPOT_KEY:
        return {"error": "HUBSPOT_API_KEY not set", "synced": 0}

    try:
        from routers.leads import get_supabase
        db = get_supabase()
        if not db:
            return {"error": "Supabase not connected", "synced": 0}

        result = db.table("leads").select("*").order("created_at", desc=True).limit(200).execute()
        leads = result.data or []

        synced = 0
        failed = 0
        for lead in leads:
            contact_id = await push_lead_to_hubspot(lead)
            if contact_id:
                synced += 1
            else:
                failed += 1

        log.info(f"HubSpot bulk sync: {synced} synced, {failed} failed")
        return {"synced": synced, "failed": failed, "total": len(leads)}

    except Exception as e:
        log.error(f"HubSpot bulk sync error: {e}")
        return {"error": str(e), "synced": 0}
