"""
Phase 4 — The Optimizer (Feedback Loop)
- Reads incoming replies, classifies sentiment via Claude
- Escalates "interested" to Slack immediately
- Snoozes "not now" leads for 90 days
- Updates A/B performance table so Personalizer picks winning variants
- Sends Friday KPI report
"""

import os
import asyncio
import asyncpg
import anthropic
from slack_sdk.web.async_client import AsyncWebClient
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

DB_URL        = os.getenv("LEADOS_DB_URL", "")
CLAUDE_MODEL  = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
SLACK_TOKEN   = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.getenv("SLACK_ALERT_CHANNEL", "")

claude = anthropic.AsyncAnthropic()
slack  = AsyncWebClient(token=SLACK_TOKEN)

async def classify_reply(reply_body: str) -> str:
    """Returns: interested | not_now | unsubscribe | neutral"""
    msg = await claude.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16,
        system=(
            "Classify this sales email reply into exactly one of: "
            "interested | not_now | unsubscribe | neutral. "
            "Return only the label, nothing else."
        ),
        messages=[{"role": "user", "content": reply_body}],
    )
    label = msg.content[0].text.strip().lower()
    return label if label in ("interested", "not_now", "unsubscribe", "neutral") else "neutral"

async def escalate_to_slack(lead: dict, outreach: dict):
    text = (
        f":fire: *Hot lead replied — escalate now!*\n"
        f"*Name:* {lead['first_name']} {lead['last_name']}\n"
        f"*Title:* {lead['title']} @ {lead['company']}\n"
        f"*Email:* {lead['email']}\n"
        f"*Subject:* {outreach['subject']}\n"
        f"*Reply:* {outreach['reply_body'][:500]}"
    )
    await slack.chat_postMessage(channel=SLACK_CHANNEL, text=text)

async def update_ab_performance(conn, event_type: str, variant: str, field: str):
    await conn.execute(
        f"""
        INSERT INTO ab_performance (event_type, variant, {field})
        VALUES ($1, $2, 1)
        ON CONFLICT (event_type, variant) DO UPDATE
        SET {field} = ab_performance.{field} + 1, updated_at = NOW()
        """,
        event_type, variant,
    )

async def process_replies():
    """Process new replies fetched from SendGrid inbound parse webhook."""
    conn = await asyncpg.connect(DB_URL)
    try:
        # Fetch outreach with unclassified replies
        rows = await conn.fetch(
            """
            SELECT o.id, o.lead_id, o.reply_body, o.subject, o.variant,
                   te.event_type,
                   l.first_name, l.last_name, l.title, l.company, l.email
            FROM outreach o
            JOIN leads l ON l.id = o.lead_id
            LEFT JOIN trigger_events te ON te.id = o.trigger_event_id
            WHERE o.replied_at IS NOT NULL
              AND o.reply_sentiment IS NULL
              AND o.reply_body IS NOT NULL
            """
        )

        for row in rows:
            sentiment = await classify_reply(row["reply_body"])

            await conn.execute(
                "UPDATE outreach SET reply_sentiment = $1 WHERE id = $2",
                sentiment, row["id"],
            )

            if sentiment == "interested":
                await conn.execute(
                    "UPDATE leads SET status = 'booked', updated_at = NOW() WHERE id = $1",
                    row["lead_id"],
                )
                await escalate_to_slack(dict(row), dict(row))
                print(f"[Optimizer] INTERESTED → Slack alert sent for {row['email']}")

            elif sentiment == "not_now":
                snooze = datetime.now(timezone.utc) + timedelta(days=90)
                await conn.execute(
                    """
                    UPDATE leads SET status = 'snoozed', snooze_until = $1,
                                     updated_at = NOW()
                    WHERE id = $2
                    """,
                    snooze, row["lead_id"],
                )
                print(f"[Optimizer] Snoozed {row['email']} for 90 days")

            elif sentiment == "unsubscribe":
                await conn.execute(
                    "UPDATE leads SET status = 'dead', updated_at = NOW() WHERE id = $1",
                    row["lead_id"],
                )

            # Update A/B table
            if row["event_type"] and row["variant"]:
                await update_ab_performance(
                    conn, row["event_type"], row["variant"], "reply_count"
                )

            await conn.execute(
                """
                INSERT INTO activity_log (lead_id, agent, action, detail)
                VALUES ($1, 'optimizer', 'reply_classified', $2::jsonb)
                """,
                row["lead_id"],
                f'{{"sentiment": "{sentiment}"}}',
            )

        print(f"[Optimizer] {len(rows)} replies classified")
    finally:
        await conn.close()

async def send_friday_report():
    conn = await asyncpg.connect(DB_URL)
    try:
        stats = await conn.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE sent_at IS NOT NULL AND sent_at >= NOW() - INTERVAL '7 days') AS sent,
                COUNT(*) FILTER (WHERE opened_at IS NOT NULL AND opened_at >= NOW() - INTERVAL '7 days') AS opened,
                COUNT(*) FILTER (WHERE replied_at IS NOT NULL AND replied_at >= NOW() - INTERVAL '7 days') AS replied,
                COUNT(*) FILTER (WHERE reply_sentiment = 'interested' AND replied_at >= NOW() - INTERVAL '7 days') AS booked
            FROM outreach
            """
        )
        sent = stats["sent"] or 0
        text = (
            f":bar_chart: *LeadOS Weekly Report*\n"
            f"Week ending {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
            f"• Sent: {sent}\n"
            f"• Opened: {stats['opened']} ({int(stats['opened']/sent*100) if sent else 0}%)\n"
            f"• Replied: {stats['replied']} ({int(stats['replied']/sent*100) if sent else 0}%)\n"
            f"• Interested/Booked: {stats['booked']}"
        )
        await slack.chat_postMessage(channel=SLACK_CHANNEL, text=text)
        print("[Optimizer] Friday report sent to Slack")
    finally:
        await conn.close()

if __name__ == "__main__":
    import sys
    if "--report" in sys.argv:
        asyncio.run(send_friday_report())
    else:
        asyncio.run(process_replies())
