"""
Agent 2 — The Personalizer ("The Writer")
Claude drafts a 3-sentence cold email for each Tier-1 lead with a verified trigger.
Applies A/B variant selection based on optimizer feedback.
"""

import os
import asyncio
import asyncpg
import anthropic
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

DB_URL       = os.getenv("LEADOS_DB_URL", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
FROM_NAME    = os.environ.get("SENDGRID_FROM_NAME", "Your Name")

claude = anthropic.AsyncAnthropic()

SYSTEM_PROMPT = """You are the Personalizer agent in LeadOS. You write cold outreach emails
that convert. Rules:
- EXACTLY 3 sentences in the body (no more, no less)
- Sentence 1: reference the specific trigger event naturally — no "I saw that..." clichés
- Sentence 2: connect their situation to a concrete outcome we deliver
- Sentence 3: one soft CTA (e.g. "Worth a 15-min chat?")
- No fluff, no buzzwords, no emojis
- Value prop: "compress sales cycle 30% with AI-driven lead prioritization, no added headcount"
- Sign as a human rep, not AI
Return JSON: {"subject": str, "body": str}"""

async def best_variant(conn, event_type: str) -> str:
    """Pick the A/B variant with higher open rate for this event type."""
    rows = await conn.fetch(
        """
        SELECT variant,
               CASE WHEN sent_count > 0 THEN open_count::float / sent_count ELSE 0 END AS open_rate
        FROM ab_performance
        WHERE event_type = $1
        ORDER BY open_rate DESC
        LIMIT 1
        """,
        event_type,
    )
    return rows[0]["variant"] if rows else "A"

VARIANT_INSTRUCTIONS = {
    "A": "Lead with the trigger event. Keep a peer-to-peer, casual-professional tone.",
    "B": "Lead with the business outcome first, then weave in the trigger as proof of timing.",
}

async def draft_email(lead: dict, event: dict, variant: str) -> dict | None:
    variant_note = VARIANT_INSTRUCTIONS.get(variant, VARIANT_INSTRUCTIONS["A"])
    prompt = (
        f"Lead: {lead['first_name']} {lead['last_name']}, {lead['title']} @ {lead['company']}\n"
        f"Trigger event ({event['event_type']}): {event['headline']}\n"
        f"Source: {event['source_url']}\n"
        f"Variant instruction: {variant_note}\n"
        f"Rep name: {FROM_NAME}\n\n"
        "Write the subject line and 3-sentence email body. Return JSON only."
    )

    msg = await claude.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    try:
        return json.loads(msg.content[0].text)
    except Exception:
        return None

async def run_personalizer():
    conn = await asyncpg.connect(DB_URL)
    try:
        rows = await conn.fetch(
            """
            SELECT l.id AS lead_id, l.first_name, l.last_name, l.title, l.company,
                   l.email, l.timezone,
                   te.id AS event_id, te.event_type, te.headline, te.source_url
            FROM leads l
            JOIN trigger_events te ON te.lead_id = l.id
            WHERE l.tier = 1
              AND l.status = 'new'
              AND NOT EXISTS (
                  SELECT 1 FROM outreach o WHERE o.lead_id = l.id
              )
            LIMIT 50
            """
        )

        drafted = 0
        for row in rows:
            lead  = dict(row)
            event = {"event_type": row["event_type"], "headline": row["headline"],
                     "source_url": row["source_url"]}
            variant = await best_variant(conn, event["event_type"])
            email   = await draft_email(lead, event, variant)

            if not email:
                print(f"[Personalizer] Draft failed for {lead['company']}")
                continue

            await conn.execute(
                """
                INSERT INTO outreach (lead_id, trigger_event_id, subject, body, variant)
                VALUES ($1, $2, $3, $4, $5)
                """,
                lead["lead_id"], row["event_id"], email["subject"], email["body"], variant,
            )
            await conn.execute(
                """
                INSERT INTO activity_log (lead_id, agent, action, detail)
                VALUES ($1, 'personalizer', 'email_drafted', $2::jsonb)
                """,
                lead["lead_id"],
                f'{{"variant": "{variant}", "subject": "{email["subject"]}"}}',
            )
            drafted += 1
            print(f"[Personalizer] {lead['company']} ({variant}) → {email['subject']}")

        print(f"[Personalizer] Done — {drafted}/{len(rows)} emails drafted")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_personalizer())
