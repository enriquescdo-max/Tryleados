"""
SendGrid Inbound Parse Webhook Server
Receives email reply webhooks from SendGrid and writes them to the DB.
Run: uvicorn agents.webhook_server:app --port 8080

Configure SendGrid: Settings → Inbound Parse → add your domain/URL
"""

import os
import asyncpg
from datetime import datetime, timezone
from fastapi import FastAPI, Form, Request
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

DB_URL = os.environ["LEADOS_DB_URL"]
app = FastAPI()

@app.post("/webhook/inbound-email")
async def inbound_email(
    request: Request,
    to: str = Form(default=""),
    from_: str = Form(alias="from", default=""),
    subject: str = Form(default=""),
    text: str = Form(default=""),
):
    """Called by SendGrid when a lead replies. Match to outreach record and save."""
    sender_email = from_.split("<")[-1].rstrip(">").strip().lower()

    conn = await asyncpg.connect(DB_URL)
    try:
        # Find the lead by email
        lead = await conn.fetchrow(
            "SELECT id FROM leads WHERE LOWER(email) = $1", sender_email
        )
        if not lead:
            return {"status": "unknown_sender"}

        # Update the most recent outreach for this lead
        await conn.execute(
            """
            UPDATE outreach
            SET replied_at = $1, reply_body = $2
            WHERE lead_id = $3
              AND sent_at IS NOT NULL
              AND replied_at IS NULL
            """,
            datetime.now(timezone.utc), text[:4000], lead["id"],
        )
        await conn.execute(
            "UPDATE leads SET status = 'replied', updated_at = NOW() WHERE id = $1",
            lead["id"],
        )
    finally:
        await conn.close()

    return {"status": "ok"}

@app.post("/webhook/sendgrid-events")
async def sendgrid_events(request: Request):
    """Called by SendGrid for open/click/bounce tracking events."""
    events = await request.json()
    conn = await asyncpg.connect(DB_URL)
    try:
        for event in events:
            sg_id    = event.get("sg_message_id", "").split(".")[0]
            ev_type  = event.get("event")
            ts       = datetime.fromtimestamp(event.get("timestamp", 0), tz=timezone.utc)

            if ev_type == "open":
                await conn.execute(
                    "UPDATE outreach SET opened_at = $1 WHERE sendgrid_id = $2 AND opened_at IS NULL",
                    ts, sg_id,
                )
    finally:
        await conn.close()
    return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "running", "service": "LeadOS Webhook Server"}
