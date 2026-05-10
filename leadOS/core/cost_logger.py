import os
from datetime import datetime, timezone
from supabase import create_client

_sb = None

def _client():
    global _sb
    if _sb is None:
        _sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    return _sb

# Pricing per 1M tokens (USD)
PRICING = {
    "claude-sonnet-4-6":          {"input": 3.00,  "output": 15.00},
    "claude-haiku-4-5-20251001":  {"input": 0.25,  "output": 1.25},
}

def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING.get(model, {"input": 3.00, "output": 15.00})
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000

def log_cost(
    agent_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    vertical: str = None,
    session_id: str = None,
    metadata: dict = None,
) -> dict:
    cost_usd = compute_cost(model, input_tokens, output_tokens)
    row = {
        "agent_name": agent_name,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
        "vertical": vertical,
        "session_id": session_id,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _client().table("agent_costs").insert(row).execute()
    return row

def get_cost_summary(agent_name: str = None, vertical: str = None) -> dict:
    q = _client().table("agent_costs").select("cost_usd, input_tokens, output_tokens")
    if agent_name:
        q = q.eq("agent_name", agent_name)
    if vertical:
        q = q.eq("vertical", vertical)
    rows = q.execute().data
    return {
        "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
        "total_input_tokens": sum(r["input_tokens"] for r in rows),
        "total_output_tokens": sum(r["output_tokens"] for r in rows),
        "call_count": len(rows),
    }
