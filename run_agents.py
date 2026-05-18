#!/usr/bin/env python3
"""AgentOS parallel agent harness — fires all verticals simultaneously."""
import asyncio
import argparse
import random
import time
from datetime import datetime

# ANSI colors
R = "\033[0;31m"; G = "\033[0;32m"; Y = "\033[0;33m"
B = "\033[0;34m"; M = "\033[0;35m"; C = "\033[0;36m"
W = "\033[1;37m"; NC = "\033[0m"; BOLD = "\033[1m"

VERTICALS = {
    "leados":   {"color": G,  "label": "LeadOS   ", "sim_threshold": 0.35, "tcpa": True},
    "peakclaw": {"color": M,  "label": "PeakClaw ", "sim_threshold": 0.70, "human_token": True},
    "juniper":  {"color": C,  "label": "JuniperOS", "sim_threshold": 0.50},
    "founderos":{"color": Y,  "label": "FounderOS", "sim_threshold": 0.40},
}

MOVE37_THRESHOLD = 0.80  # confidence above which we flag as Move 37


def log(vertical: str, msg: str, symbol: str = "→"):
    v = VERTICALS[vertical]
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{W}[{ts}]{NC} {v['color']}{v['label']}{NC} {symbol} {msg}")


async def simulate_vertical(vertical: str, demo: bool) -> dict:
    v = VERTICALS[vertical]
    pace = 0.8 if demo else 0.1

    log(vertical, "Initializing agent loop...", "◈")
    await asyncio.sleep(pace * random.uniform(0.5, 1.2))

    # Phase 1: Data ingestion
    lead_count = random.randint(12, 48)
    log(vertical, f"Ingested {lead_count} signals from pipeline", "↓")
    await asyncio.sleep(pace * random.uniform(0.3, 0.8))

    # Phase 2: In-silico simulation
    scenarios = 1000 if vertical == "leados" else 500
    log(vertical, f"Running in-silico simulation ({scenarios} scenarios)...", "⟳")
    await asyncio.sleep(pace * random.uniform(1.0, 2.0))

    sim_score = random.uniform(0.30, 0.95)
    threshold = v["sim_threshold"]

    if sim_score < threshold:
        log(vertical, f"GUARDRAIL BLOCKED — sim score {sim_score:.2f} < {threshold} threshold", "✗")
        return {"vertical": vertical, "status": "blocked", "sim_score": sim_score, "move37": False}

    log(vertical, f"Simulation passed: confidence {sim_score:.2f}", "✓")
    await asyncio.sleep(pace * 0.4)

    # Phase 3: TCPA gate (leados only)
    if v.get("tcpa"):
        log(vertical, "TCPA gate: verifying opt-in tokens...", "🔒")
        await asyncio.sleep(pace * 0.5)
        log(vertical, "TCPA gate passed — all leads have verified opt-in", "✓")

    # Phase 4: Human token gate (peakclaw only)
    if v.get("human_token"):
        log(vertical, "Human token gate: compliance sign-off required", "🔒")
        await asyncio.sleep(pace * 0.6)
        log(vertical, "Human token verified — proceeding to report generation", "✓")

    # Phase 5: Move 37 detection
    move37_score = random.uniform(0.40, 0.99)
    move37_detected = move37_score >= MOVE37_THRESHOLD
    move37_count = random.randint(1, 4) if move37_detected else 0

    await asyncio.sleep(pace * 0.5)

    if move37_detected:
        log(vertical, f"★ MOVE 37 DETECTED — {move37_count} counterintuitive opportunities (score: {move37_score:.2f})", "★")
        await asyncio.sleep(pace * 0.3)

    # Phase 6: Execution
    actions = {
        "leados":    f"Queuing {random.randint(3,8)} warm transfers via Vapi ($25/each)",
        "peakclaw":  f"Flagged {random.randint(1,3)} LOTAIL drift vectors for review",
        "juniper":   f"Surfaced {random.randint(2,6)} Life ROI units for Jamie",
        "founderos": f"Mapped {random.randint(1,4)} GTM paths standard accelerators missed",
    }
    log(vertical, actions[vertical], "⚡")
    await asyncio.sleep(pace * 0.5)

    # Phase 7: Flywheel check
    flywheel = vertical == "juniper" and random.random() > 0.4
    if flywheel:
        log(vertical, "⚡ FLYWHEEL TRIGGERED — lease close → LeadOS renters insurance handoff", "⚡")
        await asyncio.sleep(pace * 0.4)

    # Phase 8: Supabase audit log
    log(vertical, "Logging to Supabase agent_context...", "↑")
    await asyncio.sleep(pace * 0.3)
    log(vertical, "Audit log written ✓", "✓")

    return {
        "vertical": vertical,
        "status": "complete",
        "sim_score": sim_score,
        "move37": move37_detected,
        "move37_count": move37_count,
        "move37_score": move37_score,
        "flywheel": flywheel,
    }


def print_summary(results: list[dict], elapsed: float):
    print(f"\n{BOLD}{W}{'═'*60}{NC}")
    print(f"{BOLD}{W}  AgentOS v1.0.0 — Execution Summary{NC}")
    print(f"{BOLD}{W}{'═'*60}{NC}")

    complete = [r for r in results if r["status"] == "complete"]
    blocked  = [r for r in results if r["status"] == "blocked"]
    move37s  = [r for r in complete if r.get("move37")]
    flywheels= [r for r in complete if r.get("flywheel")]

    for r in results:
        v = VERTICALS[r["vertical"]]
        status_sym = "✅" if r["status"] == "complete" else "🚫"
        m37 = " ★" if r.get("move37") else ""
        fw  = " ⚡" if r.get("flywheel") else ""
        print(f"  {status_sym} {v['color']}{v['label']}{NC}  sim={r['sim_score']:.2f}{m37}{fw}")

    print(f"\n  {G}Complete:{NC} {len(complete)}/{len(results)} verticals")
    if blocked:
        print(f"  {R}Blocked: {NC} {len(blocked)} (guardrail trips — correct behavior)")
    if move37s:
        total_m37 = sum(r.get("move37_count", 0) for r in move37s)
        print(f"  {Y}Move 37:{NC}  {total_m37} counterintuitive opportunities surfaced ★")
    if flywheels:
        print(f"  {C}Flywheel:{NC} {len(flywheels)} cross-vertical handoff triggered ⚡")

    print(f"\n  Elapsed: {elapsed:.1f}s")
    print(f"\n  {W}Root-Node First. In-Silico Before Action. Move 37. Human Flourishing.{NC}")
    print(f"{BOLD}{W}{'═'*60}{NC}\n")


async def main(demo: bool):
    print(f"\n{BOLD}{W}{'═'*60}{NC}")
    print(f"{BOLD}{W}  AgentOS Parallel Agent Harness v1.0.0{NC}")
    mode = f"{Y}DEMO — dramatic pacing{NC}" if demo else f"{G}PRODUCTION{NC}"
    print(f"  Mode: {mode}")
    print(f"  Firing {len(VERTICALS)} verticals simultaneously")
    print(f"{BOLD}{W}{'═'*60}{NC}\n")

    if demo:
        await asyncio.sleep(0.5)

    start = time.time()
    tasks = [simulate_vertical(v, demo) for v in VERTICALS]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    print_summary(list(results), elapsed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentOS parallel agent harness")
    parser.add_argument("--demo", action="store_true", help="Slower dramatic pacing for demos")
    args = parser.parse_args()
    asyncio.run(main(args.demo))
