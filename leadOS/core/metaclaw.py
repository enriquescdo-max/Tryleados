"""
MetaClaw — Per-User Memory Injection Layer (P10)
Every Claude API call in LeadOS prepends the user's context via this module.
"""
import logging
from typing import Optional, Dict, Any

log = logging.getLogger("LeadOS.MetaClaw")


def build_user_context(user_memory: Optional[Dict] = None, leads_summary: Optional[Dict] = None) -> str:
    """
    Build a context string injected at the top of every Claude system prompt.
    Reads from Supabase user_memory + live orchestrator state.
    """
    if not user_memory and not leads_summary:
        return ""

    parts = ["[USER CONTEXT]"]

    if user_memory:
        industry = user_memory.get("industry", "insurance")
        icp      = user_memory.get("icp_description", "")
        states   = ", ".join(user_memory.get("target_states") or [])
        hours    = user_memory.get("preferred_call_hours", "9am-5pm CST")
        notes    = user_memory.get("memory_notes", "")
        total    = user_memory.get("total_leads_generated", 0)
        transfers = user_memory.get("total_transfers", 0)

        parts.append(f"Industry: {industry}")
        if icp:
            parts.append(f"ICP: {icp}")
        if states:
            parts.append(f"Target states: {states}")
        parts.append(f"Preferred call hours: {hours}")
        parts.append(f"Total leads generated: {total} | Total transfers: {transfers}")
        if notes:
            parts.append(f"Notes: {notes}")

    if leads_summary:
        total_leads = leads_summary.get("total", 0)
        qualified   = leads_summary.get("qualified", 0)
        avg_score   = leads_summary.get("avg_score", 0)
        parts.append(f"Current pipeline: {total_leads} leads, {qualified} qualified, avg score {avg_score}")

    parts.append("[END USER CONTEXT]")
    return "\n".join(parts)


async def load_user_memory(user_email: str = "") -> Dict:
    """Load user_memory from Supabase. Returns empty dict if unavailable."""
    try:
        from db import supabase_client
        if not supabase_client.is_ready():
            return {}
        import asyncio
        result = await asyncio.to_thread(
            lambda: supabase_client.client
                .table("user_memory")
                .select("*")
                .limit(1)
                .execute()
        )
        rows = result.data if hasattr(result, "data") else []
        return rows[0] if rows else {}
    except Exception as e:
        log.warning(f"MetaClaw load_user_memory failed: {e}")
        return {}


def inject_memory(system_prompt: str, user_context: str) -> str:
    """Prepend user context to any system prompt."""
    if not user_context:
        return system_prompt
    return f"{user_context}\n\n{system_prompt}"
