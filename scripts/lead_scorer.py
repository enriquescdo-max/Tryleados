"""
Phase 2 — Analytical Engine: Lead Scoring
Runs daily via cron. Pulls all leads, recalculates propensity-to-buy score,
updates tier, and logs the run.
"""

import os
import asyncio
import asyncpg
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

DB_URL = os.environ["LEADOS_DB_URL"]

# ICP signal weights (must sum to 1.0)
WEIGHTS = {
    "title":    0.35,
    "revenue":  0.25,
    "intent":   0.25,
    "trigger":  0.15,
}

TITLE_SCORES = {
    "cro": 1.0, "vp sales": 1.0, "vp of sales": 1.0,
    "head of growth": 0.95, "head of sales": 0.95,
    "founder": 0.90, "co-founder": 0.90, "ceo": 0.85,
    "revops": 0.80, "revenue operations": 0.80,
    "director of sales": 0.75, "sales manager": 0.60,
    "account executive": 0.40,
}

def score_title(title: str | None) -> float:
    if not title:
        return 0.0
    t = title.lower()
    for key, val in TITLE_SCORES.items():
        if key in t:
            return val
    return 0.2

def score_revenue(revenue: float | None) -> float:
    if not revenue or revenue <= 0:
        return 0.0
    if 1_000_000 <= revenue <= 50_000_000:
        return 1.0
    if revenue < 1_000_000:
        return max(0.0, revenue / 1_000_000)
    # above $50M — still valuable but lower ICP fit
    return max(0.3, 1.0 - (revenue - 50_000_000) / 200_000_000)

def score_intent(intent: float | None) -> float:
    return float(intent) if intent is not None else 0.0

def score_trigger(has_trigger: bool) -> float:
    return 1.0 if has_trigger else 0.0

def compute_lead_score(title, revenue, intent, has_trigger) -> float:
    raw = (
        score_title(title)   * WEIGHTS["title"]   +
        score_revenue(revenue) * WEIGHTS["revenue"] +
        score_intent(intent)  * WEIGHTS["intent"]  +
        score_trigger(has_trigger) * WEIGHTS["trigger"]
    )
    return round(min(raw, 1.0), 4)

def assign_tier(score: float) -> int:
    if score >= 0.70:
        return 1
    if score >= 0.50:
        return 2
    return 0

async def run_scoring():
    conn = await asyncpg.connect(DB_URL)
    try:
        leads = await conn.fetch(
            """
            SELECT l.id, l.title, l.company_revenue, l.intent_score,
                   EXISTS(SELECT 1 FROM trigger_events te WHERE te.lead_id = l.id) AS has_trigger
            FROM leads l
            WHERE l.status NOT IN ('dead', 'unsubscribe')
            """
        )

        updated = 0
        tier_counts = {0: 0, 1: 0, 2: 0}

        for lead in leads:
            score = compute_lead_score(
                lead["title"],
                lead["company_revenue"],
                lead["intent_score"],
                lead["has_trigger"],
            )
            tier = assign_tier(score)
            tier_counts[tier] += 1

            await conn.execute(
                """
                UPDATE leads
                SET lead_score = $1, tier = $2, updated_at = NOW()
                WHERE id = $3
                """,
                score, tier, lead["id"],
            )
            updated += 1

        # Log the scoring run
        await conn.execute(
            """
            INSERT INTO activity_log (agent, action, detail)
            VALUES ('scorer', 'daily_run', $1::jsonb)
            """,
            f'{{"leads_scored": {updated}, "tier1": {tier_counts[1]}, '
            f'"tier2": {tier_counts[2]}, "tier0": {tier_counts[0]}, '
            f'"run_at": "{datetime.now(timezone.utc).isoformat()}"}}',
        )

        print(f"[Scorer] {updated} leads scored — "
              f"Tier1={tier_counts[1]} Tier2={tier_counts[2]} Unqualified={tier_counts[0]}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_scoring())
