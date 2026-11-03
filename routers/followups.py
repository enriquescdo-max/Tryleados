"""Drafts the owner can approve. Approval does not send the message."""

from fastapi import APIRouter, HTTPException

from core.compliance import contact_decision, outbound_send_enabled
from services.agency_store import get_store

router = APIRouter(prefix="/api/leads", tags=["followups"])


@router.post("/{lead_id}/followups")
async def create_followup(lead_id: str):
    draft = get_store().save_draft(lead_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return draft


@router.post("/{lead_id}/followups/{draft_id}/approve")
async def approve_followup(lead_id: str, draft_id: str):
    draft = get_store().approve_draft(lead_id, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found.")
    return draft


@router.post("/{lead_id}/followups/{draft_id}/send")
async def send_followup(lead_id: str, draft_id: str):
    store = get_store()
    draft = store.get_draft(lead_id, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found.")
    if draft.get("status") != "approved":
        raise HTTPException(status_code=403, detail="Approve the draft before sending. Nothing was sent.")
    if not outbound_send_enabled():
        raise HTTPException(status_code=403, detail="Sending is off. Approving a draft does not send it.")
    lead = store.get_lead(lead_id) or {}
    decision = contact_decision(channel="sms", consents=store.consents_for(lead))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    raise HTTPException(status_code=403, detail="No message was sent. Copy the approved draft and send it yourself.")
