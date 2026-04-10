"""
LeadOS Supabase Persistence Layer
Saves and loads leads so they survive Railway restarts.
"""

import logging
import json
from typing import List, Dict, Any, Optional

log = logging.getLogger("LeadOS.Supabase")

_client = None


def init(supabase_url: str, supabase_service_key: str):
    """Call once at startup with credentials from config."""
    global _client
    if not supabase_url or not supabase_service_key:
        log.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY not set — persistence disabled.")
        return
    try:
        from supabase import create_client
        _client = create_client(supabase_url, supabase_service_key)
        log.info("Supabase client initialized.")
    except Exception as e:
        log.warning(f"Supabase init failed ({e}) — persistence disabled.")


def is_ready() -> bool:
    return _client is not None


def save_lead(lead_dict: Dict[str, Any]) -> bool:
    """Upsert a lead row. Returns True on success."""
    if not _client:
        return False
    try:
        row = {
            "id":                   lead_dict["id"],
            "name":                 lead_dict.get("name", ""),
            "email":                lead_dict.get("email"),
            "phone":                lead_dict.get("phone"),
            "title":                lead_dict.get("title", ""),
            "company":              lead_dict.get("company", ""),
            "source":               lead_dict.get("source", "web_crawler"),
            "status":               lead_dict.get("status", "new"),
            "ai_score":             lead_dict.get("ai_score"),
            "ai_score_reasoning":   lead_dict.get("ai_score_reasoning"),
            "intent_signals":       json.dumps(lead_dict.get("intent_signals", [])),
            "email_verified":       lead_dict.get("email_verified"),
            "linkedin_url":         lead_dict.get("linkedin_url"),
        }
        _client.table("leads").upsert(row).execute()
        return True
    except Exception as e:
        log.warning(f"Supabase save_lead failed: {e}")
        return False


def load_leads() -> List[Dict[str, Any]]:
    """Load all leads from Supabase. Returns list of dicts."""
    if not _client:
        return []
    try:
        result = _client.table("leads").select("*").order("created_at", desc=True).limit(5000).execute()
        rows = result.data or []
        # Parse intent_signals back from JSON string if needed
        for row in rows:
            if isinstance(row.get("intent_signals"), str):
                try:
                    row["intent_signals"] = json.loads(row["intent_signals"])
                except Exception:
                    row["intent_signals"] = []
        log.info(f"Loaded {len(rows)} leads from Supabase.")
        return rows
    except Exception as e:
        log.warning(f"Supabase load_leads failed: {e}")
        return []


def update_lead_status(lead_id: str, status: str, ai_score: Optional[int] = None,
                       ai_score_reasoning: Optional[str] = None) -> bool:
    """Patch a lead's status and score after qualification."""
    if not _client:
        return False
    try:
        patch = {"status": status}
        if ai_score is not None:
            patch["ai_score"] = ai_score
        if ai_score_reasoning is not None:
            patch["ai_score_reasoning"] = ai_score_reasoning
        _client.table("leads").update(patch).eq("id", lead_id).execute()
        return True
    except Exception as e:
        log.warning(f"Supabase update_lead_status failed: {e}")
        return False
