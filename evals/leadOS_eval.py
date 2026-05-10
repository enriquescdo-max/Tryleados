"""
Eval suite for leadOS agents.
Runs qualification scenarios and scores output quality.
Results stored in eval_results Supabase table.
"""
import os
import json
import uuid
from datetime import datetime, timezone
import anthropic
from supabase import create_client
from core.cost_logger import log_cost

EVAL_MODEL = "claude-sonnet-4-6"

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

SCENARIOS = [
    {
        "id": "auto_qualified",
        "vertical": "leadOS",
        "description": "Standard auto insurance lead — should qualify",
        "input": "I need auto insurance. I have a 2021 Toyota Camry, clean record, Austin TX 78701.",
        "expected_qualified": True,
        "expected_carriers": ["Progressive", "GEICO", "Root"],
    },
    {
        "id": "auto_dui_disqualify",
        "vertical": "leadOS",
        "description": "DUI history — non-standard, should route to Bristol West or National General",
        "input": "Need car insurance. Had a DUI 2 years ago. Drive a 2019 Honda Civic.",
        "expected_qualified": True,
        "expected_carriers": ["Bristol West", "National General"],
    },
    {
        "id": "home_qualified",
        "vertical": "leadOS",
        "description": "Homeowner seeking HO3 — should qualify",
        "input": "Looking for homeowners insurance. Single family home, 2005 build, Austin TX, $350k value.",
        "expected_qualified": True,
        "expected_carriers": ["Orion180", "Swyfft", "Sagesure", "Lemonade"],
    },
    {
        "id": "out_of_state_disqualify",
        "vertical": "leadOS",
        "description": "Out-of-market state — should not qualify for $25 lead",
        "input": "I need auto insurance in Maine.",
        "expected_qualified": False,
        "expected_carriers": [],
    },
    {
        "id": "juniper_apartment",
        "vertical": "juniper",
        "description": "Austin apartment seeker — should qualify",
        "input": "Looking for a 1BR apartment in South Austin, budget $1,400/mo, move in June.",
        "expected_qualified": True,
        "expected_carriers": [],
    },
]

JUDGE_SYSTEM = """You are an evaluator for an insurance/real estate AI agent.

Given the scenario and agent response, return JSON:
- "qualified_correctly": bool
- "carriers_mentioned": list of carrier names found in response
- "carriers_correct": bool
- "quality_score": 0-10 (helpfulness, accuracy, compliance)
- "issues": list of strings
- "reasoning": one sentence

Return only valid JSON."""

def _judge(scenario: dict, agent_response: str) -> dict:
    prompt = json.dumps({
        "scenario": scenario["description"],
        "input": scenario["input"],
        "expected_qualified": scenario["expected_qualified"],
        "expected_carriers": scenario["expected_carriers"],
        "agent_response": agent_response,
    }, indent=2)

    resp = _anthropic().messages.create(
        model=EVAL_MODEL,
        max_tokens=512,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    log_cost("eval_judge", EVAL_MODEL, resp.usage.input_tokens, resp.usage.output_tokens, scenario["vertical"])
    try:
        return json.loads(resp.content[0].text)
    except json.JSONDecodeError:
        return {"quality_score": 0, "issues": ["judge_parse_error"], "raw": resp.content[0].text}

def run_scenario(scenario: dict, agent_fn) -> dict:
    run_id = str(uuid.uuid4())
    agent_response = agent_fn(scenario["input"], vertical=scenario["vertical"])
    verdict = _judge(scenario, agent_response)

    row = {
        "run_id": run_id,
        "scenario_id": scenario["id"],
        "vertical": scenario["vertical"],
        "agent_response": agent_response,
        "verdict": verdict,
        "quality_score": verdict.get("quality_score", 0),
        "passed": verdict.get("qualified_correctly", False) and verdict.get("carriers_correct", True),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _supabase().table("eval_results").insert(row).execute()
    return row

def run_all(agent_fn, vertical_filter: str = None) -> dict:
    scenarios = [s for s in SCENARIOS if not vertical_filter or s["vertical"] == vertical_filter]
    results = [run_scenario(s, agent_fn) for s in scenarios]
    passed = sum(1 for r in results if r["passed"])
    avg_score = sum(r["quality_score"] for r in results) / len(results) if results else 0
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / len(results), 3) if results else 0,
        "avg_quality_score": round(avg_score, 2),
        "results": results,
    }
    print(f"Eval: {passed}/{len(results)} passed | avg score {avg_score:.1f}/10")
    return summary


if __name__ == "__main__":
    # Smoke test with a stub agent
    def stub_agent(text: str, vertical: str = "leadOS") -> str:
        return f"[stub] Received: {text} | vertical: {vertical}"

    run_all(stub_agent)
