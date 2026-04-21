"""
LeadOS Central Intelligence — Claude Orchestrator
The "Master Script" that runs the full pipeline in sequence:
  Scorer → Researcher → Personalizer → Deliverer → Optimizer (replies)

Can also be triggered manually with specific phases.
Usage:
  python orchestrator.py                  # full pipeline
  python orchestrator.py --phase score
  python orchestrator.py --phase research
  python orchestrator.py --phase draft
  python orchestrator.py --phase send
  python orchestrator.py --phase replies
  python orchestrator.py --report         # Friday KPI report
"""

import os
import sys
import asyncio
import asyncpg
import anthropic
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../config/.env"))

DB_URL       = os.environ["LEADOS_DB_URL"]
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
claude       = anthropic.AsyncAnthropic()

async def get_pipeline_status(conn) -> str:
    """Ask Claude to summarize the current pipeline health."""
    stats = await conn.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE tier = 1) AS tier1_total,
            COUNT(*) FILTER (WHERE tier = 1 AND status = 'new') AS tier1_new,
            COUNT(*) FILTER (WHERE status = 'sent') AS sent,
            COUNT(*) FILTER (WHERE status = 'snoozed') AS snoozed,
            COUNT(*) FILTER (WHERE status = 'booked') AS booked,
            COUNT(*) FILTER (WHERE status = 'dead') AS dead
        FROM leads
        """
    )
    bottleneck = await conn.fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE tier = 1 AND status = 'new'
                AND NOT EXISTS (SELECT 1 FROM trigger_events te WHERE te.lead_id = leads.id)
            ) AS missing_trigger,
            COUNT(*) FILTER (WHERE tier = 1 AND status = 'new'
                AND EXISTS (SELECT 1 FROM trigger_events te WHERE te.lead_id = leads.id)
                AND NOT EXISTS (SELECT 1 FROM outreach o WHERE o.lead_id = leads.id)
            ) AS missing_draft,
            COUNT(*) FILTER (WHERE tier = 1
                AND EXISTS (SELECT 1 FROM outreach o WHERE o.lead_id = leads.id AND o.sent_at IS NULL)
            ) AS pending_send
        FROM leads
        """
    )

    context = (
        f"Pipeline snapshot ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}):\n"
        f"- Tier 1 leads total: {stats['tier1_total']}\n"
        f"- Tier 1 unprocessed: {stats['tier1_new']}\n"
        f"- Missing trigger event: {bottleneck['missing_trigger']}\n"
        f"- Missing email draft: {bottleneck['missing_draft']}\n"
        f"- Pending send: {bottleneck['pending_send']}\n"
        f"- Sent: {stats['sent']} | Snoozed: {stats['snoozed']} "
        f"| Booked: {stats['booked']} | Dead: {stats['dead']}"
    )

    msg = await claude.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        system=(
            "You are the LeadOS Central Intelligence. In 2-3 sentences, "
            "diagnose the pipeline health and state the top one action needed. "
            "Be direct and data-driven."
        ),
        messages=[{"role": "user", "content": context}],
    )
    return f"\n{context}\n\nClaude's Assessment:\n{msg.content[0].text}"

async def run_full_pipeline():
    print("=" * 60)
    print("LeadOS Pipeline Starting —", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    print("=" * 60)

    conn = await asyncpg.connect(DB_URL)
    status = await get_pipeline_status(conn)
    await conn.close()
    print(status)
    print("=" * 60)

    # Import here to avoid circular issues
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scripts.lead_scorer import run_scoring
    from agents.researcher   import run_researcher
    from agents.personalizer import run_personalizer
    from agents.deliverer    import run_deliverer
    from agents.optimizer    import process_replies

    phases = [
        ("Scoring",      run_scoring),
        ("Research",     run_researcher),
        ("Drafting",     run_personalizer),
        ("Delivery",     run_deliverer),
        ("Reply Triage", process_replies),
    ]

    for name, fn in phases:
        print(f"\n── {name} Agent ──")
        try:
            await fn()
        except Exception as e:
            print(f"[Orchestrator] {name} failed: {e}")

    print("\n" + "=" * 60)
    print("LeadOS Pipeline Complete")
    print("=" * 60)

async def run_single_phase(phase: str):
    phase_map = {
        "score":    ("scripts.lead_scorer", "run_scoring"),
        "research": ("agents.researcher",   "run_researcher"),
        "draft":    ("agents.personalizer", "run_personalizer"),
        "send":     ("agents.deliverer",    "run_deliverer"),
        "replies":  ("agents.optimizer",    "process_replies"),
    }
    if phase not in phase_map:
        print(f"Unknown phase '{phase}'. Choose: {', '.join(phase_map)}")
        return
    module_path, fn_name = phase_map[phase]
    import importlib
    mod = importlib.import_module(module_path)
    fn  = getattr(mod, fn_name)
    await fn()

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--report" in args:
        from agents.optimizer import send_friday_report
        asyncio.run(send_friday_report())
    elif "--phase" in args:
        idx = args.index("--phase")
        phase = args[idx + 1] if idx + 1 < len(args) else ""
        asyncio.run(run_single_phase(phase))
    else:
        asyncio.run(run_full_pipeline())
