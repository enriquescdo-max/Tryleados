"""
LeadOS Campaigns Router
Exposes the full Growth Band playbook via REST API:
- Second Brain (knowledge management)
- Campaign Hypothesis Engine
- Stress Tester + Spintax
- LLM Lead Validation
- Campaign performance + kill switch
"""

import os
import json
import asyncio
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

log = logging.getLogger("LeadOS.Campaigns")
router = APIRouter(prefix="/api/v1/campaigns", tags=["campaigns"])

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── In-memory campaign store (replace with Supabase in production) ────────────
_campaigns: dict = {}
_generated_emails: list = []


# ── Models ────────────────────────────────────────────────────────────────────

class StressTestRequest(BaseModel):
    subject: str
    body: str
    persona: Optional[str] = None

class WriteAndTestRequest(BaseModel):
    hypothesis_id: Optional[str] = None
    persona: Optional[str] = None
    signal: Optional[str] = None
    angle: Optional[str] = None
    policy_type: Optional[str] = "auto"
    copy_hook: Optional[str] = None
    lead_context: Optional[dict] = None
    max_attempts: int = 3

class GenerateHypothesesRequest(BaseModel):
    focus_persona: Optional[str] = None
    count: int = 10

class ValidateLeadRequest(BaseModel):
    lead_name: Optional[str] = None
    lead_source: Optional[str] = None
    lead_text: Optional[str] = None
    zip_code: Optional[str] = None
    life_event: Optional[str] = None
    extra_context: Optional[dict] = None

class KnowledgeAddRequest(BaseModel):
    section: str
    filename: str
    content: str

class CampaignCreateRequest(BaseModel):
    hypothesis_id: str
    name: str

class CampaignUpdateRequest(BaseModel):
    sends: Optional[int] = None
    replies: Optional[int] = None
    status: Optional[str] = None


# ── Second Brain ──────────────────────────────────────────────────────────────

@router.get("/brain")
async def get_brain_index():
    """List all knowledge files in the Second Brain."""
    from core.second_brain import list_knowledge
    return {"knowledge": list_knowledge()}


@router.post("/brain/add")
async def add_knowledge(req: KnowledgeAddRequest):
    """Add or update a knowledge file (call transcripts, new carrier guides, etc.)."""
    from core.second_brain import add_knowledge
    ok = add_knowledge(req.section, req.filename, req.content)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write knowledge file")
    return {"status": "added", "path": f"{req.section}/{req.filename}.md"}


@router.get("/brain/load")
async def load_brain(sections: Optional[str] = None):
    """Load and return the full Second Brain context (for inspection)."""
    from core.second_brain import load_all
    section_list = sections.split(",") if sections else None
    content = load_all(section_list)
    return {"content": content, "chars": len(content)}


# ── Hypotheses ────────────────────────────────────────────────────────────────

@router.get("/hypotheses")
async def list_hypotheses():
    """Return the full hypothesis library."""
    from core.campaign_engine import get_all_hypotheses
    return {"hypotheses": get_all_hypotheses(), "count": len(get_all_hypotheses())}


@router.post("/hypotheses/generate")
async def generate_hypotheses(req: GenerateHypothesesRequest):
    """Use Claude + Second Brain to generate new campaign hypotheses."""
    if not ANTHROPIC_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")
    from core.campaign_engine import generate_hypotheses_with_claude, get_all_hypotheses
    new_hyps = await generate_hypotheses_with_claude(
        anthropic_key=ANTHROPIC_KEY,
        existing_hypotheses=get_all_hypotheses(),
        focus_persona=req.focus_persona,
        count=req.count,
    )
    return {"generated": new_hyps, "count": len(new_hyps)}


# ── Stress Tester ─────────────────────────────────────────────────────────────

@router.post("/stress-test")
async def stress_test_email(req: StressTestRequest):
    """Score an email draft 0-10. Requires 8.1+ to pass."""
    from core.stress_tester import stress_test
    result = await stress_test(
        subject=req.subject,
        body=req.body,
        persona=req.persona,
        anthropic_key=ANTHROPIC_KEY,
    )
    return result


@router.post("/write-and-test")
async def write_and_test_email(req: WriteAndTestRequest):
    """
    Full pipeline: write email from hypothesis → stress test → rewrite until 8.1+.
    Returns approved email with spintax variations ready to send.
    """
    if not ANTHROPIC_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")

    from core.campaign_engine import get_hypothesis_by_id
    from core.stress_tester import write_and_test

    # Build hypothesis from request
    if req.hypothesis_id:
        hypothesis = get_hypothesis_by_id(req.hypothesis_id)
        if not hypothesis:
            raise HTTPException(status_code=404, detail=f"Hypothesis {req.hypothesis_id} not found")
    else:
        hypothesis = {
            "id": "custom",
            "persona": req.persona or "General",
            "signal": req.signal or "General outreach",
            "angle": req.angle or "Value-based outreach",
            "policy_type": req.policy_type,
            "copy_hook": req.copy_hook or "",
        }

    result = await write_and_test(
        hypothesis=hypothesis,
        lead_context=req.lead_context,
        anthropic_key=ANTHROPIC_KEY,
        max_attempts=req.max_attempts,
    )

    # Store in memory
    if result.get("status") == "approved":
        _generated_emails.append({
            **result,
            "generated_at": datetime.utcnow().isoformat(),
            "hypothesis": hypothesis,
        })

    return result


@router.get("/emails")
async def list_generated_emails(limit: int = 50):
    """Return all approved emails generated this session."""
    return {
        "emails": _generated_emails[-limit:],
        "total": len(_generated_emails),
        "approved": sum(1 for e in _generated_emails if e.get("status") == "approved"),
    }


# ── LLM Lead Validation ───────────────────────────────────────────────────────

@router.post("/validate-lead")
async def validate_lead(req: ValidateLeadRequest):
    """
    Use Claude to validate whether a lead matches the ICP.
    Returns: icp_match, confidence, persona, insurance_need, urgency, angle, flags
    """
    if not ANTHROPIC_KEY:
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY not configured")

    try:
        import anthropic
        from core.second_brain import build_system_prompt

        system = build_system_prompt("data_researcher")

        context_parts = []
        if req.lead_name:    context_parts.append(f"Name: {req.lead_name}")
        if req.lead_source:  context_parts.append(f"Source: {req.lead_source}")
        if req.zip_code:     context_parts.append(f"ZIP: {req.zip_code}")
        if req.life_event:   context_parts.append(f"Life event: {req.life_event}")
        if req.lead_text:    context_parts.append(f"Raw text/listing: {req.lead_text[:500]}")
        if req.extra_context:context_parts.append(f"Extra: {json.dumps(req.extra_context)}")

        prompt = f"""Validate this lead against our ICP:

{chr(10).join(context_parts)}

Return JSON only."""

        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip().replace("```json","").replace("```","").strip()
        result = json.loads(text)
        result["validated_at"] = datetime.utcnow().isoformat()
        return result

    except Exception as e:
        log.error(f"Lead validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Campaign Management + Kill Switch ────────────────────────────────────────

@router.post("/")
async def create_campaign(req: CampaignCreateRequest):
    """Create a new campaign from a hypothesis."""
    from core.campaign_engine import get_hypothesis_by_id
    hyp = get_hypothesis_by_id(req.hypothesis_id)
    if not hyp:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    campaign_id = f"camp_{int(datetime.utcnow().timestamp())}"
    campaign = {
        "id": campaign_id,
        "name": req.name,
        "hypothesis": hyp,
        "status": "active",
        "sends": 0,
        "replies": 0,
        "reply_rate": 0.0,
        "tier": "new",
        "created_at": datetime.utcnow().isoformat(),
    }
    _campaigns[campaign_id] = campaign
    return campaign


@router.get("/")
async def list_campaigns():
    """List all campaigns with performance tiers."""
    from core.campaign_engine import tier_campaigns
    campaigns = list(_campaigns.values())
    tiers = tier_campaigns(campaigns)
    return {
        "campaigns": campaigns,
        "tiers": tiers,
        "kill_threshold": "< 1% reply rate after 50 sends",
        "scale_threshold": ">= 5% reply rate",
    }


@router.patch("/{campaign_id}")
async def update_campaign(campaign_id: str, req: CampaignUpdateRequest):
    """Update campaign stats — triggers automatic tier evaluation and kill switch."""
    if campaign_id not in _campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found")

    c = _campaigns[campaign_id]
    if req.sends is not None:   c["sends"] = req.sends
    if req.replies is not None: c["replies"] = req.replies
    if req.status is not None:  c["status"] = req.status

    # Recalculate reply rate
    if c["sends"] > 0:
        c["reply_rate"] = round(c["replies"] / c["sends"], 4)

    # Auto-tier
    from core.campaign_engine import tier_campaigns
    tiers = tier_campaigns([c])
    for tier, items in tiers.items():
        if items:
            c["tier"] = tier
            break

    # Kill switch
    if c["tier"] == "kill" and c["status"] == "active":
        c["status"] = "paused_auto"
        c["paused_reason"] = f"Auto-paused: reply rate {c['reply_rate']*100:.1f}% < 1% threshold after {c['sends']} sends"
        log.info(f"Campaign {campaign_id} auto-killed: {c['paused_reason']}")

    c["updated_at"] = datetime.utcnow().isoformat()
    return c


@router.get("/performance")
async def get_performance_summary():
    """Dashboard summary — what to scale, optimize, kill."""
    from core.campaign_engine import tier_campaigns
    campaigns = list(_campaigns.values())
    tiers = tier_campaigns(campaigns)

    return {
        "summary": {
            "total_campaigns": len(campaigns),
            "scale": len(tiers["scale"]),
            "optimize": len(tiers["optimize"]),
            "kill": len(tiers["kill"]),
            "new": len(tiers["new"]),
        },
        "tiers": tiers,
        "actions": {
            "scale": [c["name"] for c in tiers["scale"]],
            "kill_immediately": [c["name"] for c in tiers["kill"]],
        }
    }
