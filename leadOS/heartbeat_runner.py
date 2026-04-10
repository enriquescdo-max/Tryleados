"""
LeadOS Heartbeat Runner (P16-P18)
Runs as a Railway cron job. Called with one of:
  python heartbeat_runner.py morning_brief
  python heartbeat_runner.py lead_checker
  python heartbeat_runner.py voice_trigger

Uses the internal Railway API rather than spawning a new process.
"""
import asyncio
import httpx
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LeadOS.Heartbeat")

PORT    = os.getenv("PORT", "8000")
BASE    = f"http://0.0.0.0:{PORT}"
EMAIL   = os.getenv("ADMIN_EMAIL", os.getenv("LEADOS_ADMIN_EMAIL", "admin@leadOS.ai"))
NAME    = os.getenv("ADMIN_NAME", "Enrique")


async def run_morning_brief():
    """P16 — Send morning brief email to all active users."""
    log.info("Heartbeat: running morning brief...")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{BASE}/heartbeat/morning-brief",
                                  json={"email": EMAIL, "user_name": NAME})
        log.info(f"Morning brief response: {resp.status_code} {resp.text[:100]}")


async def run_lead_checker():
    """P17 — Check for new leads and trigger qualification pipeline."""
    log.info("Heartbeat: checking for new leads...")
    async with httpx.AsyncClient(timeout=30) as client:
        # Get current leads
        resp = await client.get(f"{BASE}/leads?limit=100")
        if resp.status_code != 200:
            log.warning(f"Lead fetch failed: {resp.status_code}")
            return

        data   = resp.json()
        leads  = data.get("leads", [])
        new_leads = [l for l in leads if l.get("status") == "new"]
        log.info(f"Lead checker: {len(leads)} total, {len(new_leads)} new")

        # Trigger heartbeat endpoint for logging
        await client.post(f"{BASE}/heartbeat/trigger")


async def run_voice_trigger():
    """P18 — Trigger voice calls for leads that entered > 60s ago and haven't been called."""
    log.info("Heartbeat: running voice trigger...")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{BASE}/leads?limit=50&status=qualified")
        if resp.status_code != 200:
            return

        leads = resp.json().get("leads", [])
        voice_cfg = await client.get(f"{BASE}/voice/config?email={EMAIL}")
        if voice_cfg.status_code != 200 or not voice_cfg.json().get("enabled"):
            log.info("Voice trigger skipped — voice not enabled for this user")
            return

        # Only call leads that have a phone number and score >= 75
        callable_leads = [
            l for l in leads
            if l.get("phone") and float(l.get("ai_score") or 0) >= 75
        ]
        log.info(f"Voice trigger: {len(callable_leads)} callable leads")

        for lead in callable_leads[:3]:  # max 3 calls per heartbeat
            resp = await client.post(f"{BASE}/voice/call",
                                      json={"lead_id": lead["id"]})
            log.info(f"Voice call initiated for {lead.get('id')}: {resp.status_code}")
            await asyncio.sleep(5)  # stagger calls


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "morning_brief"
    fn_map = {
        "morning_brief": run_morning_brief,
        "lead_checker":  run_lead_checker,
        "voice_trigger": run_voice_trigger,
    }
    fn = fn_map.get(cmd)
    if not fn:
        log.error(f"Unknown command: {cmd}. Use: morning_brief | lead_checker | voice_trigger")
        sys.exit(1)
    asyncio.run(fn())
