"""Public quote form. Creates one lead and a written-consent record. Does not list other leads."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.agency_store import get_store

router = APIRouter(prefix="/api/public", tags=["public"])

DEFAULT_CONSENT = (
    "I agree to be contacted by a licensed insurance agent by phone, text, or email about "
    "insurance quotes, including by automated technology. Consent is not a condition of purchase. "
    "Message and data rates may apply. Reply STOP to opt out."
)


class WebLead(BaseModel):
    first_name: str
    last_name: str = ""
    email: str = ""
    phone: str
    zip: str = ""
    insurance_types: list[str] = Field(default_factory=list)
    tcpa_consent: bool = False
    consent_text: str = ""
    note: str = ""


@router.post("/web-lead")
async def web_lead(body: WebLead):
    if not body.tcpa_consent:
        raise HTTPException(status_code=400, detail="Written consent is required.")
    if not body.phone.strip():
        raise HTTPException(status_code=400, detail="A phone number is required.")
    line = body.insurance_types[0] if body.insurance_types else ""
    text = body.consent_text.strip() or DEFAULT_CONSENT
    store = get_store()
    lead = store.upsert_intake({
        "name": f"{body.first_name} {body.last_name}".strip(),
        "phone": body.phone.strip(),
        "email": body.email.strip(),
        "zip": body.zip.strip(),
        "line_of_business": line,
        "summary": body.note,
        "source": "web_form",
        "callback_requested": True,
        "callback_consent": True,
        "consent_source": "web_form",
        "consent_text": text,
        "disposition": "web_form",
    })
    # The call-path consent above is not written consent. Record written consent separately.
    for channel in ("call", "sms"):
        store.add_consent({
            "lead_id": lead["id"],
            "phone": body.phone.strip(),
            "email": body.email.strip(),
            "channel": channel,
            "source": "web_form",
            "written": True,
            "scope": "owner_callback" if channel == "call" else "marketing_sms",
            "consent_text": text,
            "evidence": "Quote form checkbox",
        })
    return {"ok": True, "lead_id": lead["id"]}
