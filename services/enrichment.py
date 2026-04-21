import anthropic
import json
import os
import asyncio
from typing import Dict

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

ENRICHMENT_PROMPT = """You are an AI assistant for Enrique Saucedo, a licensed P&C insurance agent in Austin TX at We Insure. He sells auto, renters, and home insurance across 100+ carriers including Progressive, GEICO, Root, National General, Bristol West, Lemonade, Orion180, Swyfft, Sagesure.

Analyze this lead and return ONLY valid JSON (no markdown, no explanation):

Lead source: {source}
Lead text: {raw_text}
Contact: {raw_contact}

Return this exact JSON structure:
{{
  "insurance_type": "auto" | "renters" | "bundle" | "home",
  "urgency_score": 1-10,
  "carrier_recommendation": "Progressive" | "GEICO" | "Root" | "National General" | "Bristol West" | "Lemonade" | "Orion180" | "Swyfft" | "Sagesure",
  "outreach_message": "2 sentence personalized text message Enrique can send right now. Under 40 words. Mention Austin. Reference their post. Mention 100+ carriers.",
  "enrichment_reasoning": "1 sentence explaining your scoring"
}}

Urgency: 10=buying car today/just signed lease, 7-9=moving soon, 4-6=casual mention, 1-3=vague/old
Carrier: Root/Bristol West for price-sensitive auto. Progressive for bundles. Lemonade for renters under 30. Orion180/Swyfft/Sagesure for home."""


async def enrich_lead(lead: Dict) -> Dict:
    try:
        loop = asyncio.get_event_loop()
        message = await loop.run_in_executor(
            None,
            lambda: client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                messages=[{
                    "role": "user",
                    "content": ENRICHMENT_PROMPT.format(
                        source=lead.get("source", ""),
                        raw_text=lead.get("raw_text", "")[:500],
                        raw_contact=lead.get("raw_contact", "")
                    )
                }]
            )
        )
        raw = message.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw)
        return {
            **lead,
            "insurance_type": result.get("insurance_type", "auto"),
            "urgency_score": int(result.get("urgency_score", 5)),
            "carrier_recommendation": result.get("carrier_recommendation", "Progressive"),
            "outreach_message": result.get("outreach_message", ""),
            "enrichment_reasoning": result.get("enrichment_reasoning", "")
        }
    except Exception as e:
        return {
            **lead,
            "insurance_type": "auto",
            "urgency_score": 5,
            "carrier_recommendation": "Progressive",
            "outreach_message": "Hey, saw your post in Austin — I'm a local insurance agent comparing rates across 100+ carriers. Free quote in 5 min?",
            "enrichment_reasoning": f"Fallback: {str(e)}"
        }


async def enrich_all_leads(leads: list) -> list:
    enriched = []
    for i in range(0, len(leads), 5):
        batch = leads[i:i+5]
        tasks = [enrich_lead(lead) for lead in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, dict):
                enriched.append(r)
    return enriched
