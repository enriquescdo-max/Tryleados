"""
LeadOS Campaign Hypothesis Engine
Generates micro-campaign hypotheses: persona × signal × angle
Based on the Growth Band playbook — 50+ campaigns per industry
"""

import json
import asyncio
import logging
from typing import Optional
from datetime import datetime

log = logging.getLogger("LeadOS.CampaignEngine")

# ── Built-in hypothesis seed library ─────────────────────────────────────────
# These are pre-validated for insurance. Claude expands them dynamically.

SEED_HYPOTHESES = [
    # ── Renters / Apartment ──────────────────────────────────────────────────
    {
        "id": "H001",
        "persona": "New Renter",
        "signal": "Craigslist apartment listing engagement",
        "angle": "Landlord will require renters insurance — be ready before you sign",
        "policy_type": "renters",
        "channel": "email",
        "urgency": "high",
        "expected_reply_tier": "high",
        "copy_hook": "Moving soon? Your landlord will ask for proof of renters insurance on day one.",
    },
    {
        "id": "H002",
        "persona": "Apartment Locator Partner",
        "signal": "Locator posted client needing apartment on social",
        "angle": "Become their silent insurance concierge — zero work, happy clients",
        "policy_type": "renters",
        "channel": "email",
        "urgency": "medium",
        "expected_reply_tier": "high",
        "copy_hook": "Your clients need renters insurance before move-in. I handle it same-day so you never delay a lease.",
    },
    {
        "id": "H003",
        "persona": "Smart City Locating Referral",
        "signal": "Smart City Apartment Locating partner referral",
        "angle": "Warm referral — client has locator's endorsement",
        "policy_type": "renters",
        "channel": "sms",
        "urgency": "high",
        "expected_reply_tier": "very_high",
        "copy_hook": "[Locator name] sent me your way. I can get your renters insurance proof emailed to you today.",
    },
    # ── Auto ─────────────────────────────────────────────────────────────────
    {
        "id": "H004",
        "persona": "FB Marketplace Car Buyer",
        "signal": "Facebook Marketplace listing — car shopping post",
        "angle": "You'll need insurance the moment you buy — let me have a quote ready",
        "policy_type": "auto",
        "channel": "email",
        "urgency": "high",
        "expected_reply_tier": "medium",
        "copy_hook": "Buying a car soon? I can have auto insurance ready in 20 minutes so you can drive it home today.",
    },
    {
        "id": "H005",
        "persona": "Auto Dealer Finance Manager",
        "signal": "Dealer posting about high volume / new inventory",
        "angle": "I close insurance in 30 min so your buyers don't hold up delivery",
        "policy_type": "auto",
        "channel": "email",
        "urgency": "medium",
        "expected_reply_tier": "high",
        "copy_hook": "When a buyer is in your chair and needs insurance fast, I'm your call. 30-minute binder, every time.",
    },
    {
        "id": "H006",
        "persona": "Non-Standard Auto Buyer",
        "signal": "Prior claims or lapse mentioned in Craigslist car post",
        "angle": "Even with prior issues, we have carriers that will write you",
        "policy_type": "auto",
        "channel": "email",
        "urgency": "high",
        "expected_reply_tier": "medium",
        "copy_hook": "Had a lapse or a couple claims? Most agents turn you away. We have carriers that won't.",
    },
    # ── Home ─────────────────────────────────────────────────────────────────
    {
        "id": "H007",
        "persona": "New Homeowner",
        "signal": "County deed transfer record",
        "angle": "Lender needs homeowners insurance before funding — we place same day",
        "policy_type": "home",
        "channel": "email",
        "urgency": "very_high",
        "expected_reply_tier": "very_high",
        "copy_hook": "Congratulations on your new home. Your lender needs a binder before closing — I can have it to you today.",
    },
    {
        "id": "H008",
        "persona": "Realtor Partner",
        "signal": "Realtor listing property in Travis/Harris County",
        "angle": "Your buyers need insurance before closing — I specialize in hard-to-place TX homes",
        "policy_type": "home",
        "channel": "email",
        "urgency": "medium",
        "expected_reply_tier": "high",
        "copy_hook": "TX home insurance is a nightmare right now. I have carriers that accept older roofs and prior claims. Your buyers won't get stuck.",
    },
    {
        "id": "H009",
        "persona": "Difficult TX Homeowner",
        "signal": "Older property or prior claim mentioned in listing",
        "angle": "Carriers rejected you? We have specialty markets others don't",
        "policy_type": "home",
        "channel": "email",
        "urgency": "high",
        "expected_reply_tier": "high",
        "copy_hook": "Got declined or dropped by your home carrier? I place TX homes that most agents can't — older roofs, prior claims, no problem.",
    },
    # ── Bundle ───────────────────────────────────────────────────────────────
    {
        "id": "H010",
        "persona": "New Mover — Full Bundle",
        "signal": "Moving post on Reddit Austin/Houston",
        "angle": "Bundle auto + renters when you move — one call, one agent, discount",
        "policy_type": "bundle",
        "channel": "email",
        "urgency": "high",
        "expected_reply_tier": "medium",
        "copy_hook": "Moving to Austin? Bundle your auto and renters insurance together — one call, save 10-15%, coverage starts your move-in date.",
    },
    {
        "id": "H011",
        "persona": "Renewal Shoppers",
        "signal": "Renewal reminder date approaching (policy anniversary)",
        "angle": "Rates changed — let me run a quick comparison before you auto-renew",
        "policy_type": "auto",
        "channel": "email",
        "urgency": "medium",
        "expected_reply_tier": "medium",
        "copy_hook": "Your auto insurance is likely renewing soon. TX rates shifted this year — takes 10 minutes to see if you're overpaying.",
    },
    {
        "id": "H012",
        "persona": "Mortgage Broker Partner",
        "signal": "Mortgage broker closing a deal in Austin/Houston",
        "angle": "Hard TX market means clients get stuck — I have specialty carriers",
        "policy_type": "home",
        "channel": "email",
        "urgency": "medium",
        "expected_reply_tier": "high",
        "copy_hook": "How many of your closings get delayed waiting for homeowners insurance? I specialize in the hard TX cases. Let's fix that.",
    },
]

KILL_THRESHOLD_REPLY_RATE = 0.01  # 1% — pause any campaign below this
SCALE_THRESHOLD_REPLY_RATE = 0.05  # 5% — scale winners aggressively
MIN_SENDS_BEFORE_KILL = 50        # Don't kill until at least 50 sends


async def generate_hypotheses_with_claude(
    anthropic_key: str,
    existing_hypotheses: list[dict],
    focus_persona: Optional[str] = None,
    count: int = 10,
) -> list[dict]:
    """Use Claude + Second Brain to generate new campaign hypotheses."""
    try:
        import anthropic
        from core.second_brain import build_system_prompt

        system = build_system_prompt("campaign_strategist")

        existing_angles = [h["angle"] for h in existing_hypotheses]
        focus_note = f"Focus on the '{focus_persona}' persona." if focus_persona else "Cover all personas."

        prompt = f"""Generate {count} NEW micro-campaign hypotheses for a TX P&C insurance agent.

{focus_note}

Existing angles already covered (do NOT repeat these):
{chr(10).join(f'- {a}' for a in existing_angles[:20])}

For each hypothesis return JSON with these exact keys:
id, persona, signal, angle, policy_type, channel, urgency, expected_reply_tier, copy_hook

Return a JSON array only. No explanation."""

        client = anthropic.Anthropic(api_key=anthropic_key)
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        new_hyps = json.loads(text)

        # Stamp with generated IDs
        for i, h in enumerate(new_hyps):
            if not h.get("id"):
                h["id"] = f"GEN-{int(datetime.utcnow().timestamp())}-{i}"
            h["source"] = "claude_generated"

        log.info(f"Generated {len(new_hyps)} new hypotheses")
        return new_hyps

    except Exception as e:
        log.error(f"Hypothesis generation failed: {e}")
        return []


def get_all_hypotheses() -> list[dict]:
    """Return the full hypothesis library including seeds."""
    return SEED_HYPOTHESES.copy()


def tier_campaigns(campaigns: list[dict]) -> dict:
    """
    Sort campaigns into tiers based on performance:
    - scale: reply_rate >= 5% → add LinkedIn, increase volume
    - optimize: 1-5% → tweak copy, test new angles
    - kill: < 1% after 50 sends → pause immediately
    - new: not enough data yet
    """
    tiers = {"scale": [], "optimize": [], "kill": [], "new": []}

    for c in campaigns:
        sends = c.get("sends", 0)
        replies = c.get("replies", 0)
        reply_rate = replies / sends if sends > 0 else 0

        if sends < MIN_SENDS_BEFORE_KILL:
            tiers["new"].append({**c, "reply_rate": reply_rate, "sends": sends})
        elif reply_rate >= SCALE_THRESHOLD_REPLY_RATE:
            tiers["scale"].append({**c, "reply_rate": reply_rate})
        elif reply_rate >= KILL_THRESHOLD_REPLY_RATE:
            tiers["optimize"].append({**c, "reply_rate": reply_rate})
        else:
            tiers["kill"].append({**c, "reply_rate": reply_rate})

    return tiers


def get_hypothesis_by_id(hyp_id: str) -> Optional[dict]:
    for h in SEED_HYPOTHESES:
        if h["id"] == hyp_id:
            return h
    return None
