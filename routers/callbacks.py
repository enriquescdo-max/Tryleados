"""Callback queue. The owner places these calls. This router never dials."""

from fastapi import APIRouter, HTTPException

from services.agency_store import get_store

router = APIRouter(prefix="/api/callbacks", tags=["callbacks"])


@router.get("")
@router.get("/")
async def list_callbacks():
    store = get_store()
    rows = store.list_callbacks()
    return {"callbacks": rows, "count": len(rows)}


@router.post("/{lead_id}/complete")
async def complete_callback(lead_id: str):
    lead = get_store().complete_callback(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return {"lead_id": lead_id, "first_response_at": lead.get("first_response_at"), "dialed_by": "owner"}
