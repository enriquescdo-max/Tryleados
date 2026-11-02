"""Lead, consent, draft, and call records.

Tests and local runs use the in-memory store. Production sets
LEADOS_STORE=supabase after migration 004. The memory store never places a
call or sends a message.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from statistics import median

from core.compliance import contact_decision

TX_PREFIXES = ("733", "885", "75", "76", "77", "78", "79")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sla_minutes() -> int:
    raw = os.getenv("SPEED_TO_LEAD_MINUTES", "5")
    try:
        return max(1, int(raw))
    except ValueError:
        return 5


def parse_time(value):
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def out_of_texas(zip_code: str | None) -> bool:
    digits = "".join(ch for ch in (zip_code or "") if ch.isdigit())
    if len(digits) < 3:
        return False
    return not any(digits.startswith(prefix) for prefix in TX_PREFIXES)


def disqualifier_flags(intake: dict) -> list[str]:
    flags = list(intake.get("disqualifiers") or [])
    if out_of_texas(intake.get("zip")):
        flags.append("out_of_texas")
    line = (intake.get("line_of_business") or "").lower()
    if line and line not in {"home", "auto", "renters", "pet"}:
        flags.append("not_personal_lines")
    return sorted(set(flags))


def draft_followup_text(lead: dict) -> str:
    name = lead.get("raw_name") or "there"
    line = lead.get("line_of_business") or lead.get("insurance_type") or "insurance"
    return (
        f"Hi {name}, this is the licensed agent following up on your {line} question in Travis County. "
        "I can't quote a price or bind coverage by text. "
        "If you still want me to call you, reply YES. Reply STOP to opt out."
    )


def use_supabase() -> bool:
    mode = os.getenv("LEADOS_STORE", "auto").strip().lower()
    if mode == "memory":
        return False
    if mode == "supabase":
        return True
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if not url or not key or "example.supabase" in url or key == "dummy":
        return False
    return True


class MemoryStore:
    def __init__(self):
        self.leads: dict[str, dict] = {}
        self.consents: list[dict] = []
        self.drafts: list[dict] = []
        self.calls: list[dict] = []

    def reset(self):
        self.leads.clear()
        self.consents.clear()
        self.drafts.clear()
        self.calls.clear()

    def list_leads(self) -> list[dict]:
        rows = list(self.leads.values())
        rows.sort(key=lambda row: row.get("created_at") or "", reverse=True)
        return rows

    def get_lead(self, lead_id: str) -> dict | None:
        return self.leads.get(lead_id)

    def consents_for(self, lead: dict) -> list[dict]:
        phone = lead.get("phone") or lead.get("raw_contact")
        lead_id = lead.get("id")
        return [
            row for row in self.consents
            if row.get("lead_id") == lead_id or (phone and row.get("phone") == phone)
        ]

    def add_consent(self, row: dict) -> dict:
        saved = {
            "id": row.get("id") or str(uuid.uuid4()),
            "revoked_at": None,
            "written": bool(row.get("written")),
            "granted_at": row.get("granted_at") or utcnow().isoformat(),
            **row,
        }
        self.consents.append(saved)
        return saved

    def upsert_intake(self, intake: dict, *, now: datetime | None = None) -> dict:
        now = now or utcnow()
        flags = disqualifier_flags(intake)
        phone = intake.get("phone") or ""
        call_id = intake.get("call_id") or intake.get("source_call_id")
        existing = None
        if call_id:
            existing = next((row for row in self.leads.values() if row.get("source_call_id") == call_id), None)
        if existing is None and phone:
            existing = next((row for row in self.leads.values() if row.get("phone") == phone), None)

        if existing is None:
            lead_id = str(uuid.uuid4())
            due = now + timedelta(minutes=sla_minutes())
            lead = {
                "id": lead_id,
                "created_at": now.isoformat(),
                "status": "new",
                "source": intake.get("source") or "voice_inbound",
                "sla_started_at": now.isoformat(),
                "sla_due_at": due.isoformat(),
                "sla_alerted_at": None,
                "first_response_at": None,
                "urgency_score": intake.get("urgency_score") or 8,
            }
        else:
            lead = existing

        name = intake.get("name") or intake.get("raw_name") or lead.get("raw_name")
        line = intake.get("line_of_business") or lead.get("line_of_business")
        lead.update({
            "raw_name": name,
            "phone": phone or lead.get("phone"),
            "raw_contact": phone or lead.get("raw_contact"),
            "email": intake.get("email") or lead.get("email"),
            "zip": intake.get("zip") or lead.get("zip"),
            "location": intake.get("zip") or lead.get("location"),
            "language": intake.get("language") or lead.get("language"),
            "line_of_business": line,
            "insurance_type": line or lead.get("insurance_type"),
            "transcript_summary": intake.get("summary") or intake.get("transcript_summary") or lead.get("transcript_summary"),
            "disqualifiers": flags,
            "source_call_id": call_id or lead.get("source_call_id"),
            "callback_requested": bool(intake.get("callback_requested") or lead.get("callback_requested")),
        })
        self.leads[lead["id"]] = lead

        if call_id:
            self.calls.append({
                "id": str(uuid.uuid4()),
                "call_id": call_id,
                "lead_id": lead["id"],
                "from_number": phone,
                "language": lead.get("language"),
                "line_of_business": line,
                "zip": lead.get("zip"),
                "summary": lead.get("transcript_summary"),
                "disqualifiers": flags,
                "disposition": intake.get("disposition") or "intake",
                "created_at": now.isoformat(),
            })

        if intake.get("callback_consent"):
            self.add_consent({
                "lead_id": lead["id"],
                "phone": phone,
                "channel": "call",
                "source": intake.get("consent_source") or "call",
                "written": False,
                "scope": "owner_callback",
                "consent_text": intake.get("consent_text") or "Caller agreed the licensed agent may call them back.",
                "evidence": intake.get("evidence") or "Inbound call",
                "granted_at": now.isoformat(),
            })
            lead["callback_requested"] = True
        return lead

    def list_callbacks(self) -> list[dict]:
        queued = []
        for lead in self.list_leads():
            if not lead.get("callback_requested"):
                continue
            if lead.get("first_response_at"):
                continue
            decision = contact_decision(channel="owner_callback", consents=self.consents_for(lead))
            if decision.allowed:
                queued.append({**lead, "callback_reason": decision.reason})
        return queued

    def complete_callback(self, lead_id: str, *, now: datetime | None = None) -> dict | None:
        lead = self.leads.get(lead_id)
        if not lead:
            return None
        now = now or utcnow()
        lead["first_response_at"] = now.isoformat()
        lead["status"] = "contacted"
        return lead

    def save_draft(self, lead_id: str) -> dict | None:
        lead = self.leads.get(lead_id)
        if not lead:
            return None
        draft = {
            "id": str(uuid.uuid4()),
            "lead_id": lead_id,
            "body": draft_followup_text(lead),
            "status": "draft",
            "approved_at": None,
            "created_at": utcnow().isoformat(),
            "sent": False,
        }
        self.drafts.append(draft)
        return draft

    def drafts_for(self, lead_id: str) -> list[dict]:
        return [row for row in self.drafts if row["lead_id"] == lead_id]

    def approve_draft(self, lead_id: str, draft_id: str, *, now: datetime | None = None) -> dict | None:
        for draft in self.drafts:
            if draft["id"] == draft_id and draft["lead_id"] == lead_id:
                draft["status"] = "approved"
                draft["approved_at"] = (now or utcnow()).isoformat()
                draft["sent"] = False
                return draft
        return None

    def get_draft(self, lead_id: str, draft_id: str) -> dict | None:
        for draft in self.drafts:
            if draft["id"] == draft_id and draft["lead_id"] == lead_id:
                return draft
        return None

    def mark_sla_alerted(self, lead_id: str, *, now: datetime | None = None):
        lead = self.leads.get(lead_id)
        if lead:
            lead["sla_alerted_at"] = (now or utcnow()).isoformat()
        return lead

    def metrics(self, *, now: datetime | None = None) -> dict:
        leads = self.list_leads()
        responses = []
        consented = 0
        for lead in leads:
            if self.consents_for(lead):
                consented += 1
            started = parse_time(lead.get("sla_started_at"))
            responded = parse_time(lead.get("first_response_at"))
            if started and responded:
                responses.append((responded - started).total_seconds())
        total = len(leads)
        return {
            "calls": len(self.calls),
            "leads": total,
            "median_response_seconds": median(responses) if responses else None,
            "consent_rate": (consented / total) if total else 0,
            "sla_breaches_open": sum(
                1 for lead in leads
                if not lead.get("first_response_at")
                and parse_time(lead.get("sla_due_at"))
                and (now or utcnow()) >= parse_time(lead.get("sla_due_at"))
            ),
        }


def evaluate_sla(store: MemoryStore, now: datetime, notifier) -> list[str]:
    """Alert the owner once when a lead is still unanswered past the SLA.

    The notifier is only for the owner. It must not contact the lead.
    """
    alerted = []
    for lead in store.list_leads():
        if lead.get("first_response_at") or lead.get("sla_alerted_at"):
            continue
        due = parse_time(lead.get("sla_due_at"))
        if due and now >= due:
            notifier(lead)
            store.mark_sla_alerted(lead["id"], now=now)
            alerted.append(lead["id"])
    return alerted


MEMORY = MemoryStore()


def get_store():
    if not use_supabase():
        return MEMORY
    from services.supabase_store import SupabaseStore
    return SupabaseStore()
