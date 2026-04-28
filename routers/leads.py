from fastapi import APIRouter, BackgroundTasks, HTTPException
import os
from datetime import datetime

router = APIRouter(prefix="/api/leads", tags=["leads"])

_supabase = None

def get_supabase():
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            return None
        try:
            from supabase import create_client
            _supabase = create_client(url, key)
        except Exception:
            return None
    return _supabase


@router.get("/stats")
async def get_stats():
    db = get_supabase()
    if not db:
        return {"total":0,"new":0,"contacted":0,"quoted":0,"closed":0,"hot_leads":0,"by_type":{}}
    try:
        all_leads = db.table("leads").select("status, urgency_score, insurance_type").execute().data
        return {
            "total": len(all_leads),
            "new": len([l for l in all_leads if l.get("status") == "new"]),
            "contacted": len([l for l in all_leads if l.get("status") == "contacted"]),
            "quoted": len([l for l in all_leads if l.get("status") == "quoted"]),
            "closed": len([l for l in all_leads if l.get("status") == "closed"]),
            "hot_leads": len([l for l in all_leads if (l.get("urgency_score") or 0) >= 8]),
            "by_type": {
                "auto":    len([l for l in all_leads if l.get("insurance_type") == "auto"]),
                "renters": len([l for l in all_leads if l.get("insurance_type") == "renters"]),
                "bundle":  len([l for l in all_leads if l.get("insurance_type") == "bundle"]),
                "home":    len([l for l in all_leads if l.get("insurance_type") == "home"]),
            }
        }
    except Exception as e:
        print(f"[LeadOS] stats error: {e}")
        return {"total":0,"new":0,"contacted":0,"quoted":0,"closed":0,"hot_leads":0,"by_type":{}}


@router.get("/")
async def get_leads(status: str = None, min_urgency: int = 1):
    db = get_supabase()
    if not db:
        return {"leads": [], "count": 0, "error": "Database not connected"}
    try:
        query = (
            db.table("leads")
            .select("*")
            .gte("urgency_score", min_urgency)
            .order("urgency_score", desc=True)
        )
        if status:
            query = query.eq("status", status)
        result = query.execute()
        return {"leads": result.data, "count": len(result.data)}
    except Exception as e:
        print(f"[LeadOS] get_leads error: {e}")
        return {"leads": [], "count": 0, "error": str(e)}


@router.patch("/{lead_id}/status")
async def update_status(lead_id: str, status: str, agent_notes: str = None, quoted_premium: float = None):
    valid = ["new", "contacted", "quoted", "closed", "not_interested"]
    if status not in valid:
        raise HTTPException(400, f"Status must be one of: {valid}")
    db = get_supabase()
    if not db:
        raise HTTPException(503, "Database not connected")
    try:
        update_data = {"status": status}
        if agent_notes: update_data["agent_notes"] = agent_notes
        if quoted_premium: update_data["quoted_premium"] = quoted_premium
        db.table("leads").update(update_data).eq("id", lead_id).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/run-scrape")
async def run_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(scrape_enrich_save)
    return {"status": "running", "message": "Scrape started. Check /api/leads in ~2 minutes."}


async def scrape_enrich_save():
    try:
        from services.apify_scraper import scrape_all_sources
        from services.enrichment import enrich_all_leads
        from services.hubspot import push_lead_to_hubspot

        print("[LeadOS] Starting scrape pipeline...")
        raw_leads = await scrape_all_sources()
        print(f"[LeadOS] Scraped {len(raw_leads)} raw leads")
        enriched_leads = await enrich_all_leads(raw_leads)
        print(f"[LeadOS] Enriched {len(enriched_leads)} leads, saving...")

        db = get_supabase()
        if db:
            for lead in enriched_leads:
                try:
                    db.table("leads").insert({
                        "source":                 lead.get("source"),
                        "raw_name":               lead.get("raw_name"),
                        "raw_contact":            lead.get("raw_contact"),
                        "raw_text":               lead.get("raw_text", "")[:1000],
                        "location":               lead.get("location", "Austin, TX"),
                        "insurance_type":         lead.get("insurance_type"),
                        "urgency_score":          lead.get("urgency_score"),
                        "carrier_recommendation": lead.get("carrier_recommendation"),
                        "outreach_message":       lead.get("outreach_message"),
                        "enrichment_reasoning":   lead.get("enrichment_reasoning"),
                        "status":                 "new",
                        "enriched_at":            datetime.utcnow().isoformat(),
                    }).execute()
                except Exception as e:
                    print(f"[LeadOS] Insert error: {e}")

        print(f"[LeadOS] Done. {len(enriched_leads)} leads saved.")

        for lead in enriched_leads:
            try:
                from services.hubspot import push_lead_to_hubspot
                contact_id = await push_lead_to_hubspot(lead)
                if contact_id:
                    print(f"[HubSpot] Contact: {contact_id}")
            except Exception as e:
                print(f"[HubSpot] Error: {e}")

    except Exception as e:
        print(f"[LeadOS] Pipeline error: {e}")
