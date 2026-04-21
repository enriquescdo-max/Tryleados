import httpx
import os
import time

HUBSPOT_BASE = "https://api.hubapi.com"
HUBSPOT_KEY = os.environ.get("HUBSPOT_API_KEY")


async def push_lead_to_hubspot(lead: dict) -> str:
    headers = {
        "Authorization": f"Bearer {HUBSPOT_KEY}",
        "Content-Type": "application/json"
    }

    contact_data = {
        "properties": {
            "firstname": lead.get("raw_name", "Unknown"),
            "phone": lead.get("raw_contact", ""),
            "hs_lead_status": "NEW",
            "hubspot_owner_id": "91195509",
            "lead_source": "LeadOS AI Scraper",
            "notes_last_contacted": lead.get("outreach_message", ""),
            "city": "Austin",
            "state": "TX",
            "insurance_type__c": lead.get("insurance_type", "auto"),
            "urgency_score__c": str(lead.get("urgency_score", 5)),
            "carrier_recommendation__c": lead.get("carrier_recommendation", "Progressive"),
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{HUBSPOT_BASE}/crm/v3/objects/contacts",
            headers=headers,
            json=contact_data
        )
        if resp.status_code in [200, 201]:
            contact_id = resp.json().get("id")
            await client.post(
                f"{HUBSPOT_BASE}/crm/v3/objects/notes",
                headers=headers,
                json={
                    "properties": {
                        "hs_note_body": (
                            f"LeadOS Lead\n"
                            f"Source: {lead.get('source')}\n"
                            f"Insurance: {lead.get('insurance_type')}\n"
                            f"Urgency: {lead.get('urgency_score')}/10\n"
                            f"Carrier: {lead.get('carrier_recommendation')}\n\n"
                            f"Outreach Script:\n{lead.get('outreach_message')}\n\n"
                            f"Raw Signal:\n{lead.get('raw_text', '')[:500]}"
                        ),
                        "hs_timestamp": str(int(time.time() * 1000))
                    },
                    "associations": [{
                        "to": {"id": contact_id},
                        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}]
                    }]
                }
            )
            return contact_id
        else:
            print(f"[HubSpot] Failed to create contact: {resp.status_code} {resp.text}")
            return None
