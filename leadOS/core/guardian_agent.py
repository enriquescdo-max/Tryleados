"""
Guardian monitors agent outputs for compliance, PII, hallucination, and cost anomalies.
Uses claude-haiku-4-5-20251001 (cheap, fast) as the monitoring model.
"""
import os
import json
from datetime import datetime, timezone
import anthropic
from supabase import create_client
from core.cost_logger import log_cost

GUARDIAN_MODEL = "claude-haiku-4-5-20251001"

_sb = None
_ac = None

def _supabase():
    global _sb
    if _sb is None:
        _sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    return _sb

def _anthropic():
    global _ac
    if _ac is None:
        _ac = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _ac

GUARDIAN_SYSTEM = """You are a compliance and safety guardian for an insurance/fintech/real estate AI system.

Review the agent output below and return JSON with these fields:
- "safe": bool — no PII leaks, no fabricated carrier names, no illegal advice
- "compliant": bool — no unlicensed insurance guidance, no RESPA violations, no UDAAP issues
- "pii_detected": list of strings — any PII types found (SSN, DOB, bank account, etc.)
- "flags": list of strings — specific issues found
- "severity": "ok" | "warn" | "block"
- "reasoning": one sentence

Carriers in scope: Progressive, GEICO, Root, National General, Bristol West, Orion180, Swyfft, Sagesure, Lemonade.
Return only valid JSON. No markdown."""

def review(
    agent_name: str,
    vertical: str,
    user_input: str,
    agent_output: str,
    session_id: str = None,
) -> dict:
    prompt = f"Agent: {agent_name}\nVertical: {vertical}\n\nUSER INPUT:\n{user_input}\n\nAGENT OUTPUT:\n{agent_output}"

    resp = _anthropic().messages.create(
        model=GUARDIAN_MODEL,
        max_tokens=512,
        system=GUARDIAN_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.content[0].text
    try:
        verdict = json.loads(raw)
    except json.JSONDecodeError:
        verdict = {"safe": False, "compliant": False, "flags": ["guardian_parse_error"], "severity": "warn", "raw": raw}

    log_cost(
        agent_name="guardian",
        model=GUARDIAN_MODEL,
        input_tokens=resp.usage.input_tokens,
        output_tokens=resp.usage.output_tokens,
        vertical=vertical,
        session_id=session_id,
    )

    _supabase().table("guardian_log").insert({
        "agent_name": agent_name,
        "vertical": vertical,
        "session_id": session_id,
        "verdict": verdict,
        "severity": verdict.get("severity", "warn"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    return verdict

def is_safe(verdict: dict) -> bool:
    return verdict.get("severity") != "block"
