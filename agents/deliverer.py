"""
Agent 3 — The Deliverer ("The SDR")
Schedules and sends drafted emails via SendGrid at the lead's local 9:30 AM.
Tracks delivery, opens, and webhook replies.
"""

import os
import asyncio
import asyncpg
import sendgrid
from sendgrid.helpers.mail import Mail
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

DB_URL        = os.getenv("LEADOS_DB_URL", "")
SG_API_KEY    = os.getenv("SENDGRID_API_KEY", "")
FROM_EMAIL    = os.getenv("SENDGRID_FROM_EMAIL", "")
FROM_NAME     = os.environ.get("SENDGRID_FROM_NAME", "Your Name")

sg = sendgrid.SendGridAPIClient(api_key=SG_API_KEY)

def next_930am_local(tz_str: str) -> datetime:
    """Return the next 9:30 AM in the lead's local timezone as UTC."""
    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        tz = ZoneInfo("America/New_York")

    now_local = datetime.now(tz)
    target = now_local.replace(hour=9, minute=30, second=0, microsecond=0)
    if target <= now_local:
        target += timedelta(days=1)
    # Skip weekends
    while target.weekday() >= 5:  # 5=Sat, 6=Sun
        target += timedelta(days=1)
    return target.astimezone(timezone.utc)

async def send_email(to_email: str, to_name: str, subject: str, body: str) -> str | None:
    """Send via SendGrid and return the message ID."""
    message = Mail(
        from_email=(FROM_EMAIL, FROM_NAME),
        to_emails=(to_email, to_name),
        subject=subject,
        plain_text_content=body,
    )
    # Enable open/click tracking
    message.tracking_settings = {
        "click_tracking": {"enable": True, "enable_text": True},
        "open_tracking": {"enable": True},
    }
    try:
        resp = sg.send(message)
        msg_id = resp.headers.get("X-Message-Id")
        return msg_id
    except Exception as e:
        print(f"[Deliverer] SendGrid error: {e}")
        return None

async def run_deliverer():
    conn = await asyncpg.connect(DB_URL)
    try:
        now_utc = datetime.now(timezone.utc)

        # Find emails scheduled to send now (±5 min window), or unscheduled drafts
        rows = await conn.fetch(
            """
            SELECT o.id AS outreach_id, o.subject, o.body,
                   l.id AS lead_id, l.email, l.first_name, l.last_name, l.timezone,
                   o.scheduled_at
            FROM outreach o
            JOIN leads l ON l.id = o.lead_id
            WHERE o.sent_at IS NULL
              AND l.status = 'new'
              AND (
                  o.scheduled_at IS NULL
                  OR o.scheduled_at <= $1
              )
            ORDER BY o.scheduled_at ASC NULLS FIRST
            LIMIT 100
            """,
            now_utc + timedelta(minutes=5),
        )

        sent = 0
        for row in rows:
            to_name = f"{row['first_name'] or ''} {row['last_name'] or ''}".strip()

            # If no schedule set yet, compute and save it, then skip until that time
            if row["scheduled_at"] is None:
                send_at = next_930am_local(row["timezone"] or "America/New_York")
                await conn.execute(
                    "UPDATE outreach SET scheduled_at = $1 WHERE id = $2",
                    send_at, row["outreach_id"],
                )
                print(f"[Deliverer] Scheduled {to_name} @ {send_at.strftime('%Y-%m-%d %H:%M UTC')}")
                continue

            # Time to send
            msg_id = await send_email(
                row["email"], to_name, row["subject"], row["body"]
            )
            if msg_id:
                await conn.execute(
                    """
                    UPDATE outreach SET sent_at = NOW(), sendgrid_id = $1 WHERE id = $2
                    """,
                    msg_id, row["outreach_id"],
                )
                await conn.execute(
                    "UPDATE leads SET status = 'sent', updated_at = NOW() WHERE id = $1",
                    row["lead_id"],
                )
                await conn.execute(
                    """
                    INSERT INTO activity_log (lead_id, agent, action, detail)
                    VALUES ($1, 'deliverer', 'email_sent', $2::jsonb)
                    """,
                    row["lead_id"],
                    f'{{"sendgrid_id": "{msg_id}", "to": "{row["email"]}"}}',
                )
                sent += 1
                print(f"[Deliverer] Sent → {row['email']} | {row['subject']}")

        print(f"[Deliverer] Done — {sent} emails sent")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_deliverer())
