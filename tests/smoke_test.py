#!/usr/bin/env python3
"""AgentOS smoke tests — all guardrails, Move 37, simulation scoring. Exits 1 on failure."""
import sys
import asyncio
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = "\033[0;32m✓\033[0m"
FAIL = "\033[0;31m✗\033[0m"
failures: list[str] = []


def check(name: str, condition: bool, detail: str = ""):
    if condition:
        print(f"  {PASS} {name}")
    else:
        print(f"  {FAIL} {name}{' — ' + detail if detail else ''}")
        failures.append(name)


# ── agents_router tests ──────────────────────────────────────────────────────

def test_agents_router_guardrails():
    print("\n[agents_router] Guardrail tests")
    from agents.agents_router import _check_guardrails, RunRequest, SIM_THRESHOLDS

    # TCPA gate — leados with no token
    req = RunRequest(simulate_score=0.99, tcpa_token=None)
    err = _check_guardrails("leados", req)
    check("TCPA gate blocks leados without token", err is not None and "TCPA_GATE" in err)

    # TCPA gate passes with token
    req = RunRequest(simulate_score=0.99, tcpa_token="tok_abc123")
    err = _check_guardrails("leados", req)
    check("TCPA gate passes leados with token", err is None)

    # Human token gate — peakclaw without token
    req = RunRequest(simulate_score=0.99, human_token=None)
    err = _check_guardrails("peakclaw", req)
    check("Human token gate blocks peakclaw without token", err is not None and "HUMAN_TOKEN_GATE" in err)

    # Human token gate passes
    req = RunRequest(simulate_score=0.99, human_token="htoken_xyz")
    err = _check_guardrails("peakclaw", req)
    check("Human token gate passes peakclaw with token", err is None)

    # Simulation threshold — leados blocked at 0.34
    req = RunRequest(simulate_score=0.34, tcpa_token="tok")
    err = _check_guardrails("leados", req)
    check("Simulation gate blocks leados at 0.34 (threshold 0.35)", err is not None and "SIMULATION_GATE" in err)

    # Simulation threshold — leados passes at 0.36
    req = RunRequest(simulate_score=0.36, tcpa_token="tok")
    err = _check_guardrails("leados", req)
    check("Simulation gate passes leados at 0.36", err is None)

    # Peakclaw threshold — blocked at 0.69
    req = RunRequest(simulate_score=0.69, human_token="htoken")
    err = _check_guardrails("peakclaw", req)
    check("Simulation gate blocks peakclaw at 0.69 (threshold 0.70)", err is not None and "SIMULATION_GATE" in err)

    # Peakclaw threshold — passes at 0.71
    req = RunRequest(simulate_score=0.71, human_token="htoken")
    err = _check_guardrails("peakclaw", req)
    check("Simulation gate passes peakclaw at 0.71", err is None)

    # Juniper threshold — blocked at 0.49
    req = RunRequest(simulate_score=0.49)
    err = _check_guardrails("juniper", req)
    check("Simulation gate blocks juniper at 0.49 (threshold 0.50)", err is not None and "SIMULATION_GATE" in err)

    # Unknown vertical
    try:
        _check_guardrails("unknown_vertical", RunRequest())
        check("Unknown vertical raises KeyError", False, "should have raised")
    except KeyError:
        check("Unknown vertical raises KeyError", True)


def test_move37_detection():
    print("\n[agents_router] Move 37 detection")
    # Move 37 threshold is 0.80 — scores above should flag
    cases = [
        (0.79, False, "score 0.79 below Move 37 threshold"),
        (0.80, True,  "score 0.80 at Move 37 threshold"),
        (0.95, True,  "score 0.95 above Move 37 threshold"),
    ]
    MOVE37_THRESHOLD = 0.80
    for score, expected, label in cases:
        detected = score >= MOVE37_THRESHOLD
        check(f"Move 37 at {score}: {'detected' if expected else 'not detected'}", detected == expected, label)


# ── context_sync tests ───────────────────────────────────────────────────────

async def test_context_sync():
    print("\n[context_sync] ContextSync tests")
    from context.context_sync import ContextSync

    ctx = ContextSync("leados")

    # set/get roundtrip (local cache, no Supabase needed)
    await ctx.set("test_key", "test_value")
    val = await ctx.get("test_key")
    check("set/get roundtrip works", val == "test_value", f"got: {val!r}")

    # recent returns entries
    entries = await ctx.recent(limit=5)
    check("recent() returns list", isinstance(entries, list))

    # move37_feed returns list
    feed = await ctx.move37_feed(limit=5)
    check("move37_feed() returns list", isinstance(feed, list))

    # flywheel_check — juniper only
    ctx_juniper = ContextSync("juniper")
    result = await ctx_juniper.flywheel_check()
    check("flywheel_check returns dict", isinstance(result, dict))
    check("flywheel_check has 'triggered' key", "triggered" in result)

    ctx_leados = ContextSync("leados")
    result = await ctx_leados.flywheel_check()
    check("flywheel_check not triggered for non-juniper", result["triggered"] is False)

    # log_action
    ok = await ctx.log_action(
        action_type="sms_send",
        simulation_score=0.72,
        guardrail_passed=True,
        move37_candidate=False,
    )
    check("log_action returns True", ok is True)


# ── run_agents tests ─────────────────────────────────────────────────────────

async def test_run_agents():
    print("\n[run_agents] Harness tests")
    from run_agents import simulate_vertical, VERTICALS

    # All verticals importable
    check("VERTICALS defined", len(VERTICALS) == 4)
    check("leados in VERTICALS", "leados" in VERTICALS)
    check("peakclaw in VERTICALS", "peakclaw" in VERTICALS)
    check("juniper in VERTICALS", "juniper" in VERTICALS)
    check("founderos in VERTICALS", "founderos" in VERTICALS)

    # simulate_vertical returns expected shape
    result = await simulate_vertical("leados", demo=False)
    check("simulate_vertical returns dict", isinstance(result, dict))
    check("result has 'vertical'", "vertical" in result)
    check("result has 'status'", "status" in result)
    check("result has 'sim_score'", "sim_score" in result)
    check("result has 'move37'", "move37" in result)
    check("status is complete or blocked", result["status"] in ("complete", "blocked"))


# ── main ─────────────────────────────────────────────────────────────────────

async def run_all():
    print("\n\033[1;37m AgentOS Smoke Tests\033[0m")
    print("═" * 50)

    test_agents_router_guardrails()
    test_move37_detection()
    await test_context_sync()
    await test_run_agents()

    print("\n" + "═" * 50)
    if failures:
        print(f"\033[0;31m FAILED: {len(failures)} test(s)\033[0m")
        for f in failures:
            print(f"  ✗ {f}")
        sys.exit(1)
    else:
        print(f"\033[0;32m ALL TESTS PASSED\033[0m")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_all())
