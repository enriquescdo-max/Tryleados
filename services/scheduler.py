from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.apify_scraper import scrape_all_sources
from services.enrichment import enrich_all_leads
from supabase import create_client
import os
import pytz
from datetime import datetime

scheduler = AsyncIOScheduler(timezone=pytz.timezone("America/Chicago"))
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


@scheduler.scheduled_job("cron", hour=7, minute=0)
async def morning_lead_drop():
    print("[LeadOS Heartbeat] 7am lead drop starting...")
    try:
        raw = await scrape_all_sources()
        enriched = await enrich_all_leads(raw)
        for lead in enriched:
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
                "status": "new",
                "enriched_at": datetime.utcnow().isoformat()
            }).execute()
        print(f"[LeadOS Heartbeat] Done. {len(enriched)} leads saved.")
    except Exception as e:
        print(f"[LeadOS Heartbeat] Error: {e}")
