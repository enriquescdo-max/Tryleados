"""Inbound receptionist posts one intake card per call. It does not dial anyone."""

from datetime import datetime, timezone

from fastapi import APIRouter, Request
from pydantic import BaseModel

from core.webhook_auth import require_voice_bridge_secret
from services.agency_store import evaluate_sla, get_store, sla_minutes

router = APIRouter(prefix="/webhook", tags=["voice"])


class IntakeBody(BaseModel):
    call_id: str | None = None
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    zip: str | None = None
    language: str | None = None
    line_of_business: str | None = None
    summary: str | None = None
    disqualifiers: list[str] = []
    callback_requested: bool = False
    callback_consent: bool = False
    consent_text: str | None = None
    disposition: str | None = None


def _owner_notifier(lead: dict):
    """Record-only by default. A configured sender may text the owner, never the lead."""
    phone = lead.get("phone")
    # The lead's number is intentionally unused. Alerts go to OWNER_ALERT_PHONE only.
    del phone


@router.post("/voice-intake")
async def voice_intake(request: Request, body: IntakeBody):
    require_voice_bridge_secret(request)
    store = get_store()
    lead = store.upsert_intake(body.model_dump())
    return {
        "lead_id": lead["id"],
        "sla_due_at": lead.get("sla_due_at"),
        "sla_minutes": sla_minutes(),
        "disqualifiers": lead.get("disqualifiers") or [],
    }


def run_sla_check(now: datetime | None = None, notifier=_owner_notifier):
    now = now or datetime.now(timezone.utc)
    return evaluate_sla(get_store(), now, notifier)
