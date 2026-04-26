"""
LeadOS Stress Tester & Spintax Engine
Phase 3 of the Growth Band playbook:
- Score every email draft 0-10 (must pass 8.1 to send)
- Randomize greetings/sign-offs with spintax for sender reputation
"""

import re
import random
import json
import asyncio
import logging
from typing import Optional

log = logging.getLogger("LeadOS.StressTester")

PASSING_SCORE = 8.1
MIN_SCORE_TO_SEND = 8.1

# ── Spintax Library ────────────────────────────────────────────────────────────

SPINTAX_LIBRARY = {
    "greeting": [
        "Hi {first_name}",
        "Hey {first_name}",
        "Hello {first_name}",
        "{first_name}",
        "Good morning {first_name}",
    ],
    "opener_bridge": [
        "Quick question —",
        "Saw something and thought of you —",
        "Reaching out because",
        "Random question but",
        "Not sure if timing is right but",
    ],
    "soft_close": [
        "Worth a quick chat?",
        "Open to a 10-minute call?",
        "Would that be helpful?",
        "Does that make sense to explore?",
        "Any interest in a quick comparison?",
    ],
    "sign_off": [
        "Thanks,",
        "Best,",
        "Appreciate your time,",
        "Talk soon,",
        "Hope to connect,",
    ],
    "urgency_phrase": [
        "before your move-in date",
        "before you drive it off the lot",
        "before your closing date",
        "same day",
        "in under 30 minutes",
    ],
    "value_phrase": [
        "I have carriers others don't",
        "I specialize in the hard TX cases",
        "most agents turn these away — I don't",
        "I've placed hundreds of TX policies this year",
        "I know the TX market inside out",
    ],
}


def resolve_spintax(text: str) -> str:
    """
    Resolve {option1|option2|option3} spintax patterns.
    Each call returns a different random variation.
    """
    def replace_spin(match):
        options = match.group(1).split("|")
        return random.choice(options).strip()

    return re.sub(r'\{([^{}]+)\}', replace_spin, text)


def inject_spintax(
    subject: str,
    body: str,
    persona_data: Optional[dict] = None,
) -> dict:
    """
    Takes a raw email and injects spintax variations for deliverability.
    Returns multiple versions for A/B testing.
    """
    first_name = (persona_data or {}).get("first_name", "there")

    # Build spintax subject
    spin_subject = subject
    if not any(x in subject for x in ["|", "{"]):
        # Auto-inject variation hints
        spin_subject = subject  # keep original as base

    # Build spintax body
    spin_body = body
    if not any(x in body for x in ["|", "{"]):
        # Auto-inject greeting variation
        greeting_options = "|".join(
            g.replace("{first_name}", first_name)
            for g in SPINTAX_LIBRARY["greeting"]
        )
        # Replace first line greeting if it matches common patterns
        for plain_greeting in [f"Hi {first_name}", f"Hey {first_name}", f"Hello {first_name}"]:
            if spin_body.startswith(plain_greeting):
                spin_body = spin_body.replace(
                    plain_greeting,
                    "{" + greeting_options + "}",
                    1
                )
                break

    # Generate 3 resolved variations
    variations = []
    for i in range(3):
        variations.append({
            "version": i + 1,
            "subject": resolve_spintax(spin_subject),
            "body": resolve_spintax(spin_body).replace("{first_name}", first_name),
        })

    return {
        "raw_subject": spin_subject,
        "raw_body": spin_body,
        "variations": variations,
        "spintax_applied": "{" in spin_subject or "{" in spin_body,
    }


# ── Stress Tester ──────────────────────────────────────────────────────────────

STRESS_TEST_CRITERIA = {
    "relevancy": "Does it explain WHY we're reaching out NOW with a specific signal?",
    "brevity": "Is the body under 80 words for cold outreach?",
    "problem_focus": "Does it lead with their pain point, not our product?",
    "specificity": "Does it name a specific situation or detail (not generic copy)?",
    "trust_signals": "Does it establish credibility without bragging?",
    "cta_clarity": "Is there exactly ONE clear, low-friction next step?",
    "tone_match": "Does the tone match the persona (casual for renters, professional for realtors)?",
    "compliance": "No deceptive claims, proper agent identification, no guarantee of coverage?",
    "uniqueness": "Would this NOT work word-for-word for a completely different prospect?",
    "deliverability": "Can key phrases be varied? No spam trigger words (free, guaranteed, act now)?",
}


def quick_score(subject: str, body: str) -> dict:
    """
    Fast rule-based pre-screening before hitting Claude API.
    Catches obvious failures immediately.
    """
    flags = []
    auto_fails = []
    score = 10.0

    word_count = len(body.split())

    # Brevity check
    if word_count > 100:
        score -= 1.5
        flags.append(f"Too long ({word_count} words) — cold emails should be <80 words")
    elif word_count > 80:
        score -= 0.5
        flags.append(f"Slightly long ({word_count} words) — trim if possible")

    # Spam trigger words
    spam_words = ["free", "guaranteed", "act now", "limited time", "click here",
                  "no obligation", "risk-free", "winner", "congratulations", "!!"]
    found_spam = [w for w in spam_words if w.lower() in body.lower() or w.lower() in subject.lower()]
    if found_spam:
        score -= 1.0
        flags.append(f"Spam triggers found: {found_spam}")

    # Generic opener red flags
    generic_openers = [
        "i hope this email finds you",
        "i hope you are doing well",
        "i wanted to reach out",
        "my name is",
        "i am writing to",
        "as per our conversation",
        "synergy",
        "circle back",
        "touch base",
        "leverage",
    ]
    found_generic = [g for g in generic_openers if g.lower() in body.lower()]
    if found_generic:
        score -= 0.5 * len(found_generic)
        flags.append(f"Generic phrases detected: {found_generic}")

    # Subject line check
    if not subject or len(subject) < 3:
        score -= 2.0
        auto_fails.append("Missing or empty subject line")

    if any(w in subject.lower() for w in ["insurance", "policy", "coverage", "quote"]):
        score -= 1.0
        flags.append("Subject line mentions 'insurance/policy/coverage' — reduces open rate for cold emails")

    # CTA check — should end with a question
    if not body.strip().endswith("?"):
        score -= 0.3
        flags.append("Email doesn't end with a question — cold emails convert better with a soft question CTA")

    # Check for personalization token
    personalization_tokens = ["{first_name}", "{{first_name}}", "[name]", "their name"]
    has_personalization = any(t in body for t in personalization_tokens) or \
                          any(c.isupper() for c in body[:50])  # heuristic: proper noun in first 50 chars
    if not has_personalization:
        score -= 0.2
        flags.append("No personalization detected — add first name or company-specific detail")

    score = max(0.0, min(10.0, round(score, 1)))
    passes = score >= PASSING_SCORE and not auto_fails

    return {
        "quick_score": score,
        "passes_quick": passes,
        "flags": flags,
        "auto_fails": auto_fails,
        "word_count": word_count,
    }


async def stress_test(
    subject: str,
    body: str,
    persona: Optional[str] = None,
    anthropic_key: Optional[str] = None,
) -> dict:
    """
    Full stress test: quick rules check + Claude deep analysis.
    Returns score, breakdown, pass/fail, and rewrite suggestions.
    """
    # Phase 1: Quick rule-based check
    quick = quick_score(subject, body)

    # If it fails basic rules badly, don't waste an API call
    if quick["auto_fails"] or quick["quick_score"] < 4.0:
        return {
            "score": quick["quick_score"],
            "pass": False,
            "method": "quick_only",
            "quick_check": quick,
            "breakdown": {},
            "rewrites": [],
            "verdict": "FAIL — Basic rules check failed. Fix auto_fails first.",
        }

    # Phase 2: Claude deep analysis
    if not anthropic_key:
        # Return quick score only
        return {
            "score": quick["quick_score"],
            "pass": quick["passes_quick"],
            "method": "quick_only",
            "quick_check": quick,
            "breakdown": {},
            "rewrites": [],
            "verdict": f"{'PASS' if quick['passes_quick'] else 'FAIL'} (quick check only — no API key)",
        }

    try:
        import anthropic
        from core.second_brain import build_system_prompt

        system = build_system_prompt("stress_tester")
        persona_note = f"The target persona is: {persona}" if persona else ""

        prompt = f"""Score this outreach email draft.

Subject: {subject}
Body:
{body}

{persona_note}

Quick pre-check results: {json.dumps(quick, indent=2)}

Score it 0-10 using the criteria in your instructions.
Passing score is 8.1/10.
Return ONLY valid JSON — no explanation outside the JSON.

Format:
{{
  "score": X.X,
  "pass": true/false,
  "breakdown": {{
    "relevancy": X.X,
    "brevity": X.X,
    "problem_focus": X.X,
    "specificity": X.X,
    "trust_signals": X.X,
    "cta_clarity": X.X,
    "tone_match": X.X,
    "compliance": X.X,
    "uniqueness": X.X,
    "deliverability": X.X
  }},
  "top_issues": ["issue1", "issue2"],
  "rewrites": [
    {{"element": "subject", "original": "...", "improved": "..."}},
    {{"element": "opening_line", "original": "...", "improved": "..."}}
  ]
}}"""

        client = anthropic.Anthropic(api_key=anthropic_key)
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(text)

        # Blend quick score insights
        result["quick_check"] = quick
        result["method"] = "claude_full"
        result["verdict"] = f"{'PASS ✅' if result['pass'] else 'FAIL ❌'} — Score: {result['score']}/10"

        return result

    except Exception as e:
        log.error(f"Stress test Claude call failed: {e}")
        return {
            "score": quick["quick_score"],
            "pass": quick["passes_quick"],
            "method": "quick_fallback",
            "quick_check": quick,
            "breakdown": {},
            "rewrites": [],
            "verdict": f"Claude unavailable — quick score: {quick['quick_score']}/10",
        }


async def write_and_test(
    hypothesis: dict,
    lead_context: Optional[dict] = None,
    anthropic_key: Optional[str] = None,
    max_attempts: int = 3,
) -> dict:
    """
    Full pipeline: write email from hypothesis → stress test → rewrite until passing.
    Returns the first draft that scores >= 8.1, up to max_attempts.
    """
    if not anthropic_key:
        return {"error": "ANTHROPIC_API_KEY required"}

    import anthropic
    from core.second_brain import build_system_prompt

    system = build_system_prompt("outreach_writer")
    lead_info = json.dumps(lead_context or {}, indent=2)

    attempts = []

    for attempt in range(1, max_attempts + 1):
        previous_feedback = ""
        if attempts:
            last = attempts[-1]
            issues = last.get("test_result", {}).get("top_issues", [])
            rewrites = last.get("test_result", {}).get("rewrites", [])
            previous_feedback = f"""
Previous attempt scored {last['test_result'].get('score', 0)}/10. FAILED.
Issues: {issues}
Suggested rewrites: {json.dumps(rewrites, indent=2)}
Rewrite the email addressing these specific issues."""

        prompt = f"""Write a cold outreach email for this campaign hypothesis:

Persona: {hypothesis.get('persona')}
Signal: {hypothesis.get('signal')}
Angle: {hypothesis.get('angle')}
Policy Type: {hypothesis.get('policy_type')}
Copy Hook: {hypothesis.get('copy_hook')}

Lead context:
{lead_info}

{previous_feedback}

Return JSON only: {{"subject": "...", "body": "..."}}
Body must be under 80 words. No bullet points. End with a soft question."""

        try:
            client = anthropic.Anthropic(api_key=anthropic_key)
            response = await asyncio.to_thread(
                client.messages.create,
                model="claude-sonnet-4-20250514",
                max_tokens=600,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
            draft = json.loads(text)

        except Exception as e:
            log.error(f"Write attempt {attempt} failed: {e}")
            continue

        # Stress test the draft
        test_result = await stress_test(
            subject=draft.get("subject", ""),
            body=draft.get("body", ""),
            persona=hypothesis.get("persona"),
            anthropic_key=anthropic_key,
        )

        attempts.append({
            "attempt": attempt,
            "draft": draft,
            "test_result": test_result,
        })

        if test_result.get("pass"):
            # Apply spintax and return
            spintax_result = inject_spintax(
                subject=draft["subject"],
                body=draft["body"],
                persona_data=lead_context,
            )
            return {
                "status": "approved",
                "attempts": attempt,
                "final_draft": draft,
                "spintax": spintax_result,
                "score": test_result["score"],
                "test_result": test_result,
                "hypothesis_id": hypothesis.get("id"),
                "ready_to_send": True,
            }

    # All attempts failed
    best = max(attempts, key=lambda a: a["test_result"].get("score", 0))
    return {
        "status": "failed_quality_gate",
        "attempts": max_attempts,
        "best_draft": best["draft"],
        "best_score": best["test_result"].get("score", 0),
        "all_attempts": attempts,
        "ready_to_send": False,
        "note": f"Could not reach {PASSING_SCORE}/10 after {max_attempts} attempts. Review manually.",
    }
