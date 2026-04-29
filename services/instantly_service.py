"""
LeadOS Instantly Service
Auto-enrolls qualified leads into email sequences.
Sequences are created per hypothesis (H001-H012).
"""

import os
import asyncio
import logging
import httpx
from typing import Optional

log = logging.getLogger("LeadOS.Instantly")

INSTANTLY_API_KEY = os.getenv("INSTANTLY_API_KEY", "")
INSTANTLY_BASE    = "https://api.instantly.ai/api/v2"

# Campaign IDs — map hypothesis ID to Instantly campaign
# These get populated when campaigns are created
CAMPAIGN_MAP: dict = {}


async def add_lead_to_campaign(
    lead: dict,
    campaign_id: str,
    email_subject: str,
    email_body: str,
    personalization: Optional[dict] = None,
) -> dict:
    """Add a single lead to an Instantly campaign."""
    if not INSTANTLY_API_KEY:
        return {"error": "INSTANTLY_API_KEY not set", "status": "skipped"}

    email = lead.get("email") or lead.get("raw_contact") or ""
    if "@" not in email:
        return {"error": "No valid email on lead", "status": "skipped"}

    first_name = (lead.get("raw_name") or lead.get("name") or "").split()[0].title()
    last_name  = " ".join((lead.get("raw_name") or "").split()[1:]).title()

    variables = {
        "first_name":   first_name,
        "last_name":    last_name,
        "policy_type":  lead.get("insurance_type") or "insurance",
        "carrier":      lead.get("carrier_recommendation") or "Progressive",
        "zip":          _extract_zip(lead.get("location") or ""),
        "city":         _extract_city(lead.get("location") or "Austin, TX"),
        "outreach":     lead.get("outreach_message") or email_body,
        **(personalization or {}),
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                f"{INSTANTLY_BASE}/lead",
                headers={
                    "Authorization": f"Bearer {INSTANTLY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "campaign_id": campaign_id,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "variables": variables,
                },
            )

            if res.status_code not in (200, 201):
                log.error(f"Instantly add_lead error {res.status_code}: {res.text[:200]}")
                return {"error": f"Instantly returned {res.status_code}", "status": "failed"}

            data = res.json()
            log.info(f"Lead {email} added to campaign {campaign_id}")
            return {
                "status": "enrolled",
                "email": email,
                "campaign_id": campaign_id,
                "lead_id": data.get("id"),
            }

    except Exception as e:
        log.error(f"Instantly add_lead error: {e}")
        return {"error": str(e), "status": "failed"}


async def create_campaign(
    name: str,
    subject: str,
    email_body: str,
    from_name: str = "Enrique Saucedo",
    from_email: str = os.getenv("LEADOS_ADMIN_EMAIL", "enrique@weinsure.com"),
    daily_limit: int = 50,
    timezone: str = "America/Chicago",
) -> dict:
    """Create a new Instantly campaign."""
    if not INSTANTLY_API_KEY:
        return {"error": "INSTANTLY_API_KEY not set"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                f"{INSTANTLY_BASE}/campaign",
                headers={
                    "Authorization": f"Bearer {INSTANTLY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "name": name,
                    "campaign_schedule": {
                        "schedules": [
                            {
                                "name": "Business hours",
                                "days": {
                                    "monday": True, "tuesday": True, "wednesday": True,
                                    "thursday": True, "friday": True, "saturday": False, "sunday": False
                                },
                                "start_hour": "08:00",
                                "end_hour": "17:00",
                                "timezone": timezone,
                            }
                        ]
                    },
                    "daily_limit": daily_limit,
                    "email_list": [{"from_name": from_name, "from_email": from_email}],
                    "sequences": [
                        {
                            "steps": [
                                {
                                    "type": "email",
                                    "delay": 0,
                                    "variants": [{"subject": subject, "body": email_body}],
                                },
                                {
                                    "type": "email",
                                    "delay": 3,
                                    "variants": [
                                        {
                                            "subject": f"Re: {subject}",
                                            "body": f"Hey {{{{first_name}}}} — just following up on my last message. Did you get a chance to look into {'{policy_type}'} coverage? I can get you a quick quote today.",
                                        }
                                    ],
                                },
                                {
                                    "type": "email",
                                    "delay": 7,
                                    "variants": [
                                        {
                                            "subject": "Last check-in",
                                            "body": f"Hey {{{{first_name}}}} — I'll keep this short. If you're still shopping for insurance, I'd love to help. One call, 10 minutes, and I'll have options ready. Otherwise I won't bug you again 🙂",
                                        }
                                    ],
                                },
                            ]
                        }
                    ],
                },
            )

            if res.status_code not in (200, 201):
                return {"error": f"Instantly returned {res.status_code}: {res.text[:100]}"}

            data = res.json()
            campaign_id = data.get("id")
            log.info(f"Instantly campaign created: {campaign_id} — {name}")
            return {"status": "created", "campaign_id": campaign_id, "name": name}

    except Exception as e:
        log.error(f"Instantly create_campaign error: {e}")
        return {"error": str(e)}


async def get_campaign_stats(campaign_id: str) -> dict:
    """Get open/reply/bounce stats for a campaign."""
    if not INSTANTLY_API_KEY:
        return {}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{INSTANTLY_BASE}/campaign/{campaign_id}/analytics",
                headers={"Authorization": f"Bearer {INSTANTLY_API_KEY}"},
            )
            return res.json() if res.status_code == 200 else {}
    except Exception:
        return {}


async def list_campaigns() -> list:
    """List all Instantly campaigns."""
    if not INSTANTLY_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(
                f"{INSTANTLY_BASE}/campaign",
                headers={"Authorization": f"Bearer {INSTANTLY_API_KEY}"},
                params={"limit": 50},
            )
            return res.json().get("items", []) if res.status_code == 200 else []
    except Exception:
        return []


def _extract_zip(location: str) -> str:
    import re
    match = re.search(r"\b(\d{5})\b", location)
    return match.group(1) if match else "78701"

def _extract_city(location: str) -> str:
    if "Austin" in location: return "Austin"
    if "Houston" in location: return "Houston"
    if "Dallas" in location: return "Dallas"
    return "Austin"
