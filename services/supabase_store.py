"""Supabase-backed store. Used only when LEADOS_STORE=supabase or a real URL is set.

Network errors surface to the caller. Tests use the memory store and do not
construct this class.
"""

from __future__ import annotations

from datetime import datetime

from services.agency_store import MemoryStore, disqualifier_flags


class SupabaseStore(MemoryStore):
    """Writes through to Supabase and keeps the same method names as memory.

    Reads prefer Supabase. If a call fails, the exception propagates so the
    API can return 503 instead of pretending the lead was saved.
    """

    def __init__(self, db=None):
        super().__init__()
        if db is None:
            from routers.leads import get_supabase
            db = get_supabase()
        if db is None:
            raise RuntimeError("Supabase is not configured.")
        self.db = db

    def upsert_intake(self, intake: dict, *, now: datetime | None = None) -> dict:
        lead = super().upsert_intake(intake, now=now)
        self.db.table("leads").upsert({
            "id": lead["id"],
            "source": lead.get("source"),
            "raw_name": lead.get("raw_name"),
            "raw_contact": lead.get("raw_contact"),
            "phone": lead.get("phone"),
            "email": lead.get("email"),
            "zip": lead.get("zip"),
            "location": lead.get("location") or lead.get("zip"),
            "language": lead.get("language"),
            "line_of_business": lead.get("line_of_business"),
            "insurance_type": lead.get("insurance_type"),
            "transcript_summary": lead.get("transcript_summary"),
            "disqualifiers": lead.get("disqualifiers") or [],
            "callback_requested": lead.get("callback_requested") or False,
            "status": lead.get("status") or "new",
            "source_call_id": lead.get("source_call_id"),
            "sla_started_at": lead.get("sla_started_at"),
            "sla_due_at": lead.get("sla_due_at"),
            "urgency_score": lead.get("urgency_score"),
        }, on_conflict="id").execute()
        if lead.get("source_call_id"):
            call = self.calls[-1]
            self.db.table("voice_calls").insert({
                "id": call["id"],
                "call_id": call["call_id"],
                "lead_id": call["lead_id"],
                "from_number": call.get("from_number"),
                "language": call.get("language"),
                "line_of_business": call.get("line_of_business"),
                "zip": call.get("zip"),
                "summary": call.get("summary"),
                "disqualifiers": disqualifier_flags(intake),
                "disposition": call.get("disposition"),
            }).execute()
        return lead

    def list_leads(self) -> list[dict]:
        result = self.db.table("leads").select("*").order("created_at", desc=True).limit(500).execute()
        return result.data or []

    def get_lead(self, lead_id: str) -> dict | None:
        result = self.db.table("leads").select("*").eq("id", lead_id).limit(1).execute()
        rows = result.data or []
        return rows[0] if rows else None

    def consents_for(self, lead: dict) -> list[dict]:
        lead_id = lead.get("id")
        if not lead_id:
            return []
        result = self.db.table("consent_ledger").select("*").eq("lead_id", lead_id).execute()
        return result.data or []

    def add_consent(self, row: dict) -> dict:
        saved = super().add_consent(row)
        self.db.table("consent_ledger").insert({
            "id": saved["id"],
            "lead_id": saved.get("lead_id"),
            "phone": saved.get("phone"),
            "email": saved.get("email"),
            "channel": saved.get("channel"),
            "source": saved.get("source"),
            "consent_text": saved.get("consent_text"),
            "written": saved.get("written"),
            "scope": saved.get("scope"),
            "evidence": saved.get("evidence"),
            "granted_at": saved.get("granted_at"),
        }).execute()
        return saved

    def save_draft(self, lead_id: str):
        draft = super().save_draft(lead_id)
        if draft:
            self.db.table("followup_drafts").insert({
                "id": draft["id"],
                "lead_id": draft["lead_id"],
                "body": draft["body"],
                "status": "draft",
            }).execute()
        return draft

    def approve_draft(self, lead_id: str, draft_id: str, *, now: datetime | None = None):
        draft = super().approve_draft(lead_id, draft_id, now=now)
        if draft:
            self.db.table("followup_drafts").update({
                "status": "approved",
                "approved_at": draft["approved_at"],
            }).eq("id", draft_id).execute()
        return draft

    def complete_callback(self, lead_id: str, *, now: datetime | None = None):
        lead = super().complete_callback(lead_id, now=now)
        if lead:
            self.db.table("leads").update({
                "first_response_at": lead["first_response_at"],
                "status": "contacted",
            }).eq("id", lead_id).execute()
        return lead

    def mark_sla_alerted(self, lead_id: str, *, now: datetime | None = None):
        lead = super().mark_sla_alerted(lead_id, now=now)
        if lead:
            self.db.table("leads").update({
                "sla_alerted_at": lead["sla_alerted_at"],
            }).eq("id", lead_id).execute()
        return lead
