"""
LeadOS Second Brain
Loads and indexes all .md knowledge files for injection into Claude prompts.
Drop-in replacement for generic prompts — gives Claude real P&C agent context.
"""

import os
import glob
from pathlib import Path
from typing import Optional

import os
BRAIN_ROOT = Path(os.environ.get("SECOND_BRAIN_PATH", str(Path(__file__).parent.parent / "second_brain")))


def load_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def load_all(sections: Optional[list[str]] = None) -> str:
    """
    Load all second brain .md files into a single context string.
    
    sections: optional list of subfolder names to load
              e.g. ["carriers", "personas"] loads only those
              None = load everything
    """
    if not BRAIN_ROOT.exists():
        return ""

    parts = []

    if sections is None:
        # Load all .md files recursively
        files = sorted(BRAIN_ROOT.rglob("*.md"))
    else:
        files = []
        for section in sections:
            section_path = BRAIN_ROOT / section
            if section_path.exists():
                files.extend(sorted(section_path.rglob("*.md")))
        # Always include icp.md
        icp = BRAIN_ROOT / "icp.md"
        if icp.exists() and icp not in files:
            files.insert(0, icp)

    for f in files:
        content = load_file(f)
        if content.strip():
            label = f.relative_to(BRAIN_ROOT).as_posix().replace(".md", "").replace("/", " > ")
            parts.append(f"## [{label}]\n{content}")

    return "\n\n---\n\n".join(parts)


def build_system_prompt(role: str = "outreach_writer") -> str:
    """
    Build a role-specific system prompt injected with Second Brain context.
    
    roles:
      outreach_writer    - writes cold emails / LinkedIn messages
      stress_tester      - scores and critiques drafts
      data_researcher    - validates ICP fit of a company/lead
      campaign_strategist - generates campaign hypotheses
      carrier_advisor    - recommends carriers for a given lead profile
    """
    brain = load_all()

    base = f"""You are an AI assistant embedded inside LeadOS, a P&C insurance lead generation platform 
built by and for a licensed insurance agent in Austin, TX.

Below is your complete knowledge base — carrier appetites, buyer personas, compliance rules, 
and proven outreach scripts. Use this context in EVERY response.

=== LEADOS KNOWLEDGE BASE ===
{brain}
=== END KNOWLEDGE BASE ===

"""

    role_prompts = {
        "outreach_writer": base + """Your job: write insurance outreach emails and messages.

Rules:
- Always lead with the specific trigger/signal that justifies the outreach
- Never mention insurance in the subject line of cold emails
- Keep initial emails under 80 words
- No bullet points in cold emails — conversational prose only
- End with ONE clear, low-friction call to action
- Never use: "I hope this email finds you well", "synergy", "circle back", "touch base"
- Always sound like a person, not a corporation
- Match the persona's pain point to our specific advantage""",

        "stress_tester": base + """Your job: score and critique outreach drafts on a scale of 0-10.

Scoring criteria (each worth up to 1.0 point):
1. Relevancy — does it explain WHY we're reaching out NOW (specific signal)?
2. Brevity — is it under 80 words for cold outreach?
3. Problem focus — does it lead with their pain, not our product?
4. Specificity — does it name a specific situation/detail (not generic)?
5. Trust signals — does it establish credibility without bragging?
6. CTA clarity — is there exactly ONE clear next step?
7. Tone match — does it match the persona's communication style?
8. Compliance — no deceptive claims, proper disclosure language?
9. Uniqueness — would this NOT work word-for-word for a different prospect?
10. Spintax ready — can key phrases be varied for deliverability?

Return JSON: {"score": X.X, "pass": true/false, "breakdown": {...}, "rewrites": [...]}
Minimum passing score: 8.1/10. If score < 8.1, provide rewrite suggestions.""",

        "data_researcher": base + """Your job: validate whether a company or individual matches our ICP.

For each lead, determine:
1. Are they in our target market? (new mover, car buyer, homeowner, referral partner)
2. What is their likely insurance need and urgency (1-10)?
3. Which buyer persona do they match?
4. What is the best outreach angle?
5. Any red flags (wrong state, no insurance need, already has coverage)?

Return JSON: {"icp_match": true/false, "confidence": 0-100, "persona": "...", "insurance_need": "...", "urgency": 1-10, "angle": "...", "flags": [...]}""",

        "campaign_strategist": base + """Your job: generate micro-campaign hypotheses.

For each hypothesis, define:
- Target persona (who exactly)
- Trigger signal (what event or behavior)
- Outreach angle (why NOW, from their perspective)
- Expected reply rate tier (high/medium/low)
- Recommended channels (email, SMS, LinkedIn, direct mail)
- Kill threshold: pause if reply rate < 1% after 50 sends

Think in combinations: persona × signal × angle = campaign.
Generate as many viable combinations as possible for the insurance industry.""",

        "carrier_advisor": base + """Your job: recommend the best carrier for a given lead profile.

Always consider: ZIP code, policy type, credit tier, prior claims, life event, vehicle age, property age.
Return ranked recommendations with specific underwriting notes the agent can use on the call.
Keep it brief and actionable — the agent is reading this while on the phone.""",
    }

    return role_prompts.get(role, base)


def get_persona_context(persona_name: str) -> str:
    """Load a specific persona file by name."""
    persona_file = BRAIN_ROOT / "personas" / f"{persona_name.lower().replace(' ', '_')}.md"
    if persona_file.exists():
        return load_file(persona_file)
    return ""


def add_knowledge(section: str, filename: str, content: str) -> bool:
    """
    Add or update a knowledge file in the second brain.
    Used for ingesting call transcripts, new carrier guides, etc.
    """
    section_path = BRAIN_ROOT / section
    section_path.mkdir(parents=True, exist_ok=True)
    file_path = section_path / f"{filename}.md"
    try:
        file_path.write_text(content, encoding="utf-8")
        return True
    except Exception:
        return False


def list_knowledge() -> dict:
    """Return a structured list of all knowledge files."""
    if not BRAIN_ROOT.exists():
        return {}
    result = {}
    for f in sorted(BRAIN_ROOT.rglob("*.md")):
        section = f.parent.relative_to(BRAIN_ROOT).as_posix()
        if section not in result:
            result[section] = []
        result[section].append({
            "name": f.stem,
            "path": str(f.relative_to(BRAIN_ROOT)),
            "size": f.stat().st_size,
        })
    return result
