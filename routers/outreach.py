"""
LeadOS Outreach Router
Endpoints for HeyGen videos, Vapi calls, Instantly sequences,
and Morning Intelligence Brief.
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

log = logging.getLogger("LeadOS.Outreach")
router = APIRouter(prefix="/api/v1/outreach", tags=["outreach"])

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# ── Models ────────────────────────────────────────────────────────────────────

class VideoRequest(BaseModel):
    lead_id: Optional[str] = None
    lead: Optional[dict] = None
    life_event: Optional[str] = None

class CallRequest(BaseModel):
    lead_id: Optional[str] = None
    lead: Optional[dict] = None

class SequenceRequest(BaseModel):
    lead: dict
    hypothesis_id: Optional[str] = "H001"
    campaign_id: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None

class BulkOutreachRequest(BaseModel):
    leads: list[dict]
    channels: list[str] = ["email"]  # email, video, call
    hypothesis_id: str = "H001"


# ── HeyGen Video Endpoints ────────────────────────────────────────────────────

@router.post("/video/generate")
async def generate_video(req: VideoRequest, background_tasks: BackgroundTasks):
    """Generate a personalized HeyGen video for a lead."""
    try:
        from services.heygen import generate_video as hg_generate
        lead = req.lead or {}
        result = await hg_generate(lead, life_event=req.life_event)
        return result
    except Exception as e:
        return {"error": str(e), "status": "failed"}


@router.get("/video/status/{video_id}")
async def video_status(video_id: str):
    """Check status of a HeyGen video."""
    try:
        from services.heygen import get_video_status
        return await get_video_status(video_id)
    except Exception as e:
        return {"error": str(e)}


@router.get("/video/avatars")
async def list_avatars():
    """List available HeyGen avatars."""
    try:
        from services.heygen import list_avatars
        return {"avatars": await list_avatars()}
    except Exception as e:
        return {"error": str(e), "avatars": []}


# ── Vapi Call Endpoints ───────────────────────────────────────────────────────

@router.post("/call/start")
async def start_call(req: CallRequest):
    """Initiate a Vapi warm transfer call to a lead. Blocked outside M-F 8am-5pm CT."""
    try:
        from services.vapi_service import create_call, is_call_compliant
        lead = req.lead or {}

        # Compliance check first
        state = (lead.get("location") or "TX").split()[-1] if lead else "TX"
        override = lead.get("call_override", False)
        compliance = is_call_compliant(state=state, override=override)
        if not compliance["allowed"]:
            return {
                "status": "blocked",
                "message": compliance["reason"],
                "next_window": compliance.get("next_window"),
                "tcpa_protected": True,
            }

        result = await create_call(lead)
        return result
    except Exception as e:
        return {"error": str(e), "status": "failed"}


@router.get("/call/compliance-check")
async def compliance_check(state: str = "TX", override: bool = False):
    """Check if it is currently legal to make outbound insurance calls."""
    try:
        from services.vapi_service import is_call_compliant
        return is_call_compliant(state=state, override=override)
    except Exception as e:
        return {"error": str(e)}


@router.get("/call/status/{call_id}")
async def call_status(call_id: str):
    """Get status and transcript of a Vapi call."""
    try:
        from services.vapi_service import get_call_status
        return await get_call_status(call_id)
    except Exception as e:
        return {"error": str(e)}


@router.get("/call/recent")
async def recent_calls(limit: int = 20):
    """List recent Vapi calls."""
    try:
        from services.vapi_service import list_calls
        return {"calls": await list_calls(limit)}
    except Exception as e:
        return {"error": str(e), "calls": []}


# ── Instantly Sequence Endpoints ──────────────────────────────────────────────

@router.post("/sequence/enroll")
async def enroll_in_sequence(req: SequenceRequest):
    """Enroll a lead in an Instantly email sequence."""
    try:
        from services.instantly_service import add_lead_to_campaign, create_campaign

        campaign_id = req.campaign_id

        # Auto-create campaign if no ID provided
        if not campaign_id:
            subject = req.subject or f"Quick question about your insurance"
            body    = req.body or req.lead.get("outreach_message") or "Hey {first_name} — I noticed you might need insurance. I can help."
            camp = await create_campaign(
                name=f"LeadOS — {req.hypothesis_id} — {datetime.now().strftime('%Y-%m-%d')}",
                subject=subject,
                email_body=body,
            )
            campaign_id = camp.get("campaign_id")
            if not campaign_id:
                return {"error": "Failed to create campaign", "details": camp}

        result = await add_lead_to_campaign(
            lead=req.lead,
            campaign_id=campaign_id,
            email_subject=req.subject or "",
            email_body=req.body or req.lead.get("outreach_message") or "",
        )
        return result

    except Exception as e:
        return {"error": str(e), "status": "failed"}


@router.get("/sequence/campaigns")
async def list_campaigns():
    """List all Instantly campaigns."""
    try:
        from services.instantly_service import list_campaigns
        return {"campaigns": await list_campaigns()}
    except Exception as e:
        return {"error": str(e), "campaigns": []}


@router.get("/sequence/stats/{campaign_id}")
async def campaign_stats(campaign_id: str):
    """Get campaign analytics from Instantly."""
    try:
        from services.instantly_service import get_campaign_stats
        return await get_campaign_stats(campaign_id)
    except Exception as e:
        return {"error": str(e)}


# ── Bulk Outreach ─────────────────────────────────────────────────────────────

@router.post("/bulk")
async def bulk_outreach(req: BulkOutreachRequest, background_tasks: BackgroundTasks):
    """
    Fire outreach across multiple channels for a batch of leads.
    Runs in background — returns immediately with job summary.
    """
    background_tasks.add_task(_run_bulk_outreach, req.leads, req.channels, req.hypothesis_id)
    return {
        "status": "queued",
        "leads_count": len(req.leads),
        "channels": req.channels,
        "hypothesis_id": req.hypothesis_id,
        "message": f"Outreach started for {len(req.leads)} leads via {req.channels}. Check /api/v1/outreach/call/recent for results.",
    }


async def _run_bulk_outreach(leads: list, channels: list, hypothesis_id: str):
    """Background task — fire outreach per lead per channel."""
    from services.heygen import generate_video
    from services.vapi_service import create_call
    from services.instantly_service import add_lead_to_campaign

    for lead in leads:
        try:
            if "video" in channels:
                video_result = await generate_video(lead)
                log.info(f"Video queued for {lead.get('raw_name')}: {video_result.get('video_id')}")
                await asyncio.sleep(0.5)

            if "call" in channels:
                call_result = await create_call(lead)
                log.info(f"Call initiated for {lead.get('raw_name')}: {call_result.get('call_id')}")
                await asyncio.sleep(2)  # Rate limit between calls

            if "email" in channels and lead.get("email"):
                pass  # Handled via /sequence/enroll

        except Exception as e:
            log.error(f"Bulk outreach error for {lead.get('raw_name')}: {e}")


# ── Morning Intelligence Brief ────────────────────────────────────────────────

@router.get("/morning-brief")
async def morning_brief():
    """
    Generate today's Morning Intelligence Brief.
    Returns top 5 hottest leads with scripts + carrier recs + strategy notes.
    Called by the 7am Heartbeat Scheduler.
    """
    try:
        from routers.leads import get_supabase
        from core.second_brain import build_system_prompt

        db = get_supabase()
        if not db:
            return {"error": "Database not connected"}

        # Get hottest new leads
        result = db.table("leads").select("*").eq("status", "new").order("urgency_score", desc=True).limit(10).execute()
        leads = result.data or []

        if not leads:
            return {"brief": "No new leads today. Run a scrape to pull fresh leads.", "leads": []}

        # Build brief with Claude
        if ANTHROPIC_KEY:
            import anthropic
            system = build_system_prompt("carrier_advisor")
            lead_summaries = "\n".join([
                f"- {l.get('raw_name','Unknown')} | {l.get('insurance_type','?')} | ZIP {l.get('location','?')} | Score {l.get('urgency_score','?')} | Source: {l.get('source','?')}"
                for l in leads[:5]
            ])

            client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=800,
                system=system,
                messages=[{
                    "role": "user",
                    "content": f"""Generate a Morning Intelligence Brief for these leads. For each lead give:
1. Best opening line to use when calling TODAY
2. Recommended carrier and why
3. Urgency level and why they need insurance now

Leads:
{lead_summaries}

Keep each entry to 2-3 sentences. Agent is a licensed TX P&C agent with 20 min per lead."""
                }],
            )
            brief_text = response.content[0].text
        else:
            brief_text = "Add ANTHROPIC_API_KEY to Railway to enable AI-generated briefs."

        return {
            "date": datetime.now().strftime("%A, %B %d, %Y"),
            "hot_leads": len([l for l in leads if (l.get("urgency_score") or 0) >= 8]),
            "new_leads": len(leads),
            "brief": brief_text,
            "leads": leads[:5],
        }

    except Exception as e:
        log.error(f"Morning brief error: {e}")
        return {"error": str(e)}


@router.get("/status")
async def outreach_status():
    """Check which outreach services are configured."""
    return {
        "heygen":    {"configured": bool(os.getenv("HEYGEN_API_KEY")), "feature": "personalized video"},
        "vapi":      {"configured": bool(os.getenv("VAPI_API_KEY")),   "feature": "AI warm transfer calls"},
        "instantly": {"configured": bool(os.getenv("INSTANTLY_API_KEY")), "feature": "email sequences"},
        "anthropic": {"configured": bool(os.getenv("ANTHROPIC_API_KEY")), "feature": "AI scripts + brief"},
    }
