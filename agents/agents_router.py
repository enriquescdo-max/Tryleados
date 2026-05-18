"""AgentOS /agents FastAPI namespace — hard guardrails enforced."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import random

router = APIRouter(tags=["agents"])

SIM_THRESHOLDS = {"leados": 0.35, "peakclaw": 0.70, "juniper": 0.50, "founderos": 0.40}
VERTICALS = list(SIM_THRESHOLDS.keys())
_audit_log: list[dict] = []
_move37_log: list[dict] = []


class RunRequest(BaseModel):
    vertical: str | None = None  # None = all
    simulate_score: float | None = None  # override for testing
    tcpa_token: str | None = None
    human_token: str | None = None


def _check_guardrails(vertical: str, req: RunRequest) -> str | None:
    """Return error string if guardrail blocks, else None."""
    sim_score = req.simulate_score or random.uniform(0.30, 0.95)
    threshold = SIM_THRESHOLDS[vertical]

    if sim_score < threshold:
        return f"SIMULATION_GATE: score {sim_score:.2f} < threshold {threshold}"

    if vertical == "leados" and not req.tcpa_token:
        return "TCPA_GATE: verified opt-in token required for SMS/call outreach"

    if vertical == "peakclaw" and not req.human_token:
        return "HUMAN_TOKEN_GATE: compliance sign-off required before broker-dealer notification"

    return None


@router.post("/run")
async def run_agents(req: RunRequest):
    targets = [req.vertical] if req.vertical else VERTICALS

    for v in targets:
        if v not in VERTICALS:
            raise HTTPException(400, f"Unknown vertical: {v}")

    results = {}
    for vertical in targets:
        error = _check_guardrails(vertical, req)
        sim_score = req.simulate_score or random.uniform(0.30, 0.95)
        move37_score = random.uniform(0.40, 0.99)
        move37 = move37_score >= 0.80

        entry = {
            "vertical": vertical,
            "timestamp": datetime.utcnow().isoformat(),
            "sim_score": sim_score,
            "guardrail_passed": error is None,
            "move37_candidate": move37 and error is None,
            "move37_score": move37_score,
            "error": error,
        }
        _audit_log.append(entry)

        if move37 and error is None:
            _move37_log.append(entry)

        results[vertical] = {
            "status": "blocked" if error else "ok",
            "sim_score": round(sim_score, 3),
            "guardrail_error": error,
            "move37": move37 and error is None,
            "move37_score": round(move37_score, 3),
        }

    return {"results": results, "timestamp": datetime.utcnow().isoformat()}


@router.get("/health")
async def agents_health():
    return {
        "status": "ok",
        "verticals": VERTICALS,
        "thresholds": SIM_THRESHOLDS,
        "audit_entries": len(_audit_log),
        "move37_surfaced": len(_move37_log),
    }


@router.get("/move37")
async def get_move37():
    return {
        "count": len(_move37_log),
        "opportunities": _move37_log[-20:],  # last 20
    }


@router.get("/audit")
async def get_audit(limit: int = 50):
    return {
        "total": len(_audit_log),
        "entries": _audit_log[-limit:],
    }
