from fastapi import APIRouter, BackgroundTasks, HTTPException
from supabase import create_client
import os
from services.apify_scraper import scrape_all_sources
from services.enrichment import enrich_all_leads
from datetime import datetime

router = APIRouter(prefix="/api/leads", tags=["leads"])
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


@router.post("/run-scrape")
async def run_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(scrape_enrich_save)
    return {"status": "running", "message": "Lead scrape started. Check /api/leads in ~2 minutes."}


async def scrape_enrich_save():
    try:
        print("[LeadOS] Starting scrape pipeline...")
        raw_leads = await scrape_all_sources()
        print(f"[LeadOS] Scraped {len(raw_leads)} raw leads")
        enriched_leads = await enrich_all_leads(raw_leads)
        print(f"[LeadOS] Enriched {len(enriched_leads)} leads, saving to Supabase...")
        for lead in enriched_leads:
            supabase.table("leads").insert({
                "source": lead.get("source"),
                "raw_name": lead.get("raw_name"),
                "raw_contact": lead.get("raw_contact"),
                "raw_text": lead.get("raw_text", "")[:1000],
                "location": lead.get("location", "Austin, TX"),
                "insurance_type": lead.get("insurance_type"),
                "urgency_score": lead.get("urgency_score"),
                "carrier_recommendation": lead.get("carrier_recommendation"),
                "outreach_message": lead.get("outreach_message"),
                "enrichment_reasoning": lead.get("enrichment_reasoning"),
                "status": "new",
                "enriched_at": datetime.utcnow().isoformat()
            }).execute()
        print(f"[LeadOS] Done. {len(enriched_leads)} leads saved.")
    except Exception as e:
        print(f"[LeadOS] Pipeline error: {e}")


@router.get("/")
async def get_leads(status: str = None, min_urgency: int = 1):
    query = supabase.table("leads").select("*").gte("urgency_score", min_urgency).order("urgency_score", desc=True)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return {"leads": result.data, "count": len(result.data)}


@router.patch("/{lead_id}/status")
async def update_status(lead_id: str, status: str, agent_notes: str = None, quoted_premium: float = None):
    valid = ["new", "contacted", "quoted", "closed", "not_interested"]
    if status not in valid:
        raise HTTPException(400, f"Status must be one of: {valid}")
    update_data = {"status": status}
    if agent_notes:
        update_data["agent_notes"] = agent_notes
    if quoted_premium:
        update_data["quoted_premium"] = quoted_premium
    supabase.table("leads").update(update_data).eq("id", lead_id).execute()
    return {"success": True}


@router.get("/stats")
async def get_stats():
    all_leads = supabase.table("leads").select("status, urgency_score, insurance_type").execute().data
    return {
        "total": len(all_leads),
        "new": len([l for l in all_leads if l["status"] == "new"]),
        "contacted": len([l for l in all_leads if l["status"] == "contacted"]),
        "quoted": len([l for l in all_leads if l["status"] == "quoted"]),
        "closed": len([l for l in all_leads if l["status"] == "closed"]),
        "hot_leads": len([l for l in all_leads if l.get("urgency_score", 0) >= 8]),
        "by_type": {
            "auto": len([l for l in all_leads if l.get("insurance_type") == "auto"]),
            "renters": len([l for l in all_leads if l.get("insurance_type") == "renters"]),
            "bundle": len([l for l in all_leads if l.get("insurance_type") == "bundle"])
        }
    }
