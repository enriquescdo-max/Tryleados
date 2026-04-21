"""
Agent 1 — The Researcher ("The Stalker")
Finds one verified trigger event per Tier-1 lead using Tavily web search.
Claude orchestrates: it selects the best event type and validates relevance.
"""

import os
import asyncio
import asyncpg
import anthropic
from tavily import AsyncTavilyClient
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

DB_URL      = os.environ["LEADOS_DB_URL"]
TAVILY_KEY  = os.environ["TAVILY_API_KEY"]
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

claude = anthropic.AsyncAnthropic()
tavily = AsyncTavilyClient(api_key=TAVILY_KEY)

TRIGGER_QUERIES = [
    "{company} funding round 2024 2025",
    "{company} new hire VP OR CRO OR Head site:linkedin.com OR techcrunch.com",
    "{company} product launch announcement",
    "{company} OR {name} AI growth revenue",
]

async def find_trigger(lead: dict) -> dict | None:
    """Run searches, then ask Claude to pick the best trigger event."""
    results = []
    for template in TRIGGER_QUERIES:
        query = template.format(
            company=lead["company"] or "",
            name=f"{lead['first_name']} {lead['last_name']}",
        )
        try:
            resp = await tavily.search(query, max_results=3, search_depth="basic")
            results.extend(resp.get("results", []))
        except Exception as e:
            print(f"[Researcher] Search error for {query}: {e}")

    if not results:
        return None

    # Deduplicate by URL
    seen, unique = set(), []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    # Ask Claude to identify the single best trigger event
    snippets = "\n".join(
        f"[{i+1}] {r['title']} — {r['url']}\n{r.get('content','')[:300]}"
        for i, r in enumerate(unique[:10])
    )

    system = (
        "You are the Researcher agent in LeadOS. Your job is to identify ONE genuine "
        "trigger event (funding, key hire, product launch, or relevant executive post) "
        "that a salesperson can reference naturally in a cold email. "
        "Return JSON only: {\"event_type\": str, \"headline\": str, \"source_url\": str} "
        "or {\"event_type\": null} if nothing credible was found."
    )
    prompt = (
        f"Lead: {lead['first_name']} {lead['last_name']}, {lead['title']} @ {lead['company']}\n\n"
        f"Search results:\n{snippets}\n\n"
        "Pick the single most relevant trigger event. Return JSON only."
    )

    msg = await claude.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=256,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    try:
        data = json.loads(msg.content[0].text)
        return data if data.get("event_type") else None
    except Exception:
        return None

async def run_researcher():
    conn = await asyncpg.connect(DB_URL)
    try:
        # Only research Tier-1 leads that are still 'new' (not yet researched)
        leads = await conn.fetch(
            """
            SELECT l.id, l.first_name, l.last_name, l.title, l.company, l.email
            FROM leads l
            WHERE l.tier = 1
              AND l.status = 'new'
              AND NOT EXISTS (
                  SELECT 1 FROM trigger_events te WHERE te.lead_id = l.id
              )
            LIMIT 50
            """
        )

        found = 0
        for lead in leads:
            event = await find_trigger(dict(lead))
            if event:
                await conn.execute(
                    """
                    INSERT INTO trigger_events (lead_id, event_type, headline, source_url)
                    VALUES ($1, $2, $3, $4)
                    """,
                    lead["id"], event["event_type"], event["headline"], event["source_url"],
                )
                await conn.execute(
                    """
                    INSERT INTO activity_log (lead_id, agent, action, detail)
                    VALUES ($1, 'researcher', 'trigger_found', $2::jsonb)
                    """,
                    lead["id"], f'{{"event_type": "{event["event_type"]}", '
                                f'"headline": "{event["headline"]}"}}',
                )
                found += 1
                print(f"[Researcher] {lead['company']} → {event['event_type']}: {event['headline'][:80]}")
            else:
                print(f"[Researcher] No trigger found for {lead['company']}")

        print(f"[Researcher] Done — {found}/{len(leads)} trigger events found")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_researcher())
