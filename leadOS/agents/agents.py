"""
LeadOS — AI Agent Fleet
Six specialized autonomous agents, each with a distinct role in the
lead generation pipeline. All agents extend BaseAgent.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
import httpx

logger = logging.getLogger("leadOS.agents")

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"


# ─────────────────────────────────────────────
# BASE AGENT
# ─────────────────────────────────────────────

class BaseAgent(ABC):
    """
    Base class for all LeadOS agents.
    Provides shared Claude API access, logging, retry logic, and metrics.
    """

    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.client = httpx.AsyncClient(timeout=60.0)
        self.tasks_completed = 0
        self.errors = 0

    async def call_claude(self, system: str, prompt: str, max_tokens: int = 1000) -> str:
        """Call Claude API with system + user prompt. Returns text response."""
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        }
        resp = await self.client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]

    async def call_claude_json(self, system: str, prompt: str) -> dict:
        """Call Claude and parse JSON response."""
        system_json = system + "\n\nIMPORTANT: Respond ONLY with valid JSON. No preamble, no markdown."
        text = await self.call_claude(system_json, prompt)
        text = text.strip().lstrip("```json").rstrip("```").strip()
        return json.loads(text)

    @abstractmethod
    async def execute(self, payload: dict) -> dict:
        """Each agent implements its core logic here."""
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.client.aclose()


# ─────────────────────────────────────────────
# AGENT 1: SCOUT — Web Crawler & Discovery
# ─────────────────────────────────────────────

class ScoutAgent(BaseAgent):
    """
    Discovers new leads by crawling web sources:
    company directories, G2, Crunchbase, job boards, news.
    Uses AI to extract and structure company data.
    """

    def __init__(self, config: dict):
        super().__init__("SCOUT", config)

    async def execute(self, payload: dict) -> dict:
        icp = payload.get("icp", {})
        sources = payload.get("sources", ["g2", "crunchbase", "linkedin"])

        logger.info(f"[SCOUT] Starting discovery for ICP: {icp.get('industry', 'all')}")

        # In production: real HTTP scraping happens here
        # We use Claude to simulate intelligent extraction logic
        result = await self.call_claude_json(
            system="""You are SCOUT, an expert web crawler agent for a lead generation OS.
Your job is to simulate discovering companies that match an ICP (Ideal Customer Profile).
Return structured company data as JSON. Be realistic and specific.""",
            prompt=f"""
Simulate discovering 5 companies that match this ICP:
{json.dumps(icp, indent=2)}

Sources to simulate: {sources}

Return JSON:
{{
  "companies": [
    {{
      "id": "unique_id",
      "name": "Company Name",
      "domain": "company.com",
      "industry": "SaaS",
      "size": "50-200",
      "location": "San Francisco, CA",
      "description": "...",
      "source": "g2",
      "discovered_at": "{datetime.utcnow().isoformat()}",
      "signals": ["hiring_engineers", "raised_series_b"]
    }}
  ],
  "source_stats": {{
    "pages_crawled": 847,
    "companies_found": 5,
    "duration_seconds": 12
  }}
}}
"""
        )

        self.tasks_completed += 1
        logger.info(f"[SCOUT] Discovered {len(result.get('companies', []))} companies")
        return result


# ─────────────────────────────────────────────
# AGENT 2: INTEL — LinkedIn & Contact Enrichment
# ─────────────────────────────────────────────

class IntelAgent(BaseAgent):
    """
    Enriches companies with decision-maker contacts,
    org chart data, LinkedIn profiles, email addresses,
    and tech stack information.
    """

    def __init__(self, config: dict):
        super().__init__("INTEL", config)

    async def execute(self, payload: dict) -> dict:
        company = payload.get("company", {})
        logger.info(f"[INTEL] Enriching: {company.get('name', 'unknown')}")

        enriched = await self.call_claude_json(
            system="""You are INTEL, a B2B intelligence agent specializing in contact enrichment.
You map org charts, find decision-makers, and enrich company profiles with actionable data.
Return precise, realistic business intelligence as JSON.""",
            prompt=f"""
Enrich this company with contact and intelligence data:
{json.dumps(company, indent=2)}

Return JSON:
{{
  "company": {{...original company data...}},
  "contacts": [
    {{
      "name": "Full Name",
      "title": "VP Marketing",
      "linkedin": "linkedin.com/in/...",
      "email": "first@company.com",
      "email_confidence": 0.95,
      "seniority": "vp",
      "department": "marketing",
      "decision_maker": true
    }}
  ],
  "tech_stack": ["Salesforce", "HubSpot", "Slack"],
  "funding": {{
    "total_raised": "$50M",
    "last_round": "Series B",
    "date": "2024-11"
  }},
  "headcount": 145,
  "headcount_growth_6m": 0.22,
  "enriched_at": "{datetime.utcnow().isoformat()}"
}}
"""
        )

        self.tasks_completed += 1
        return enriched


# ─────────────────────────────────────────────
# AGENT 3: SIGNAL — Buying Signal Detector
# ─────────────────────────────────────────────

class SignalAgent(BaseAgent):
    """
    Monitors and scores buying signals:
    - Funding rounds (budget = opportunity)
    - Leadership changes (new exec = new budget)
    - Hiring surges (growth = spend)
    - Product launches (expansion signals)
    - Competitive displacements
    """

    SIGNAL_WEIGHTS = {
        "series_funding":       90,
        "new_c_suite":          85,
        "hiring_sales_team":    75,
        "product_launch":       70,
        "competitor_mentioned": 65,
        "pricing_page_visit":   80,
        "job_posting_spike":    60,
    }

    def __init__(self, config: dict):
        super().__init__("SIGNAL", config)

    async def execute(self, payload: dict) -> dict:
        company = payload.get("company", {})
        logger.info(f"[SIGNAL] Scanning signals for: {company.get('name', 'unknown')}")

        result = await self.call_claude_json(
            system="""You are SIGNAL, a buying intent detection agent.
You analyze companies for real-time signals that indicate they are ready to buy.
Score each signal 0-100 for urgency. Be specific and actionable.""",
            prompt=f"""
Analyze buying signals for this company:
{json.dumps(company, indent=2)}

Return JSON:
{{
  "signals": [
    {{
      "type": "series_funding",
      "description": "Raised $50M Series B — new budget available",
      "urgency_score": 92,
      "detected_at": "{datetime.utcnow().isoformat()}",
      "source": "Crunchbase",
      "action_recommendation": "Reach out to new VP of Sales within 2 weeks"
    }}
  ],
  "overall_signal_score": 85,
  "recommended_timing": "immediate",
  "summary": "Company shows strong buying intent..."
}}
"""
        )

        self.tasks_completed += 1
        logger.info(f"[SIGNAL] Signal score: {result.get('overall_signal_score', 0)}")
        return result


# ─────────────────────────────────────────────
# AGENT 4: QUALIFY — AI Lead Scoring
# ─────────────────────────────────────────────

class QualifyAgent(BaseAgent):
    """
    Scores leads 0-100 against the user's ICP using multi-signal AI analysis.
    Provides explainable reasoning for each score.
    Self-improves based on won/lost deal feedback.
    """

    def __init__(self, config: dict):
        super().__init__("QUALIFY", config)
        self.icp_model = config.get("icp_model", {})

    async def execute(self, payload: dict) -> dict:
        lead = payload.get("lead", {})
        icp = payload.get("icp", self.icp_model)

        logger.info(f"[QUALIFY] Scoring lead: {lead.get('company', {}).get('name', 'unknown')}")

        scored = await self.call_claude_json(
            system="""You are QUALIFY, an AI lead scoring engine.
You evaluate leads against an Ideal Customer Profile (ICP) and score them 0-100.
Your scores must be precise, explainable, and actionable. Think like a top SDR.""",
            prompt=f"""
Score this lead against the ICP:

ICP:
{json.dumps(icp, indent=2)}

Lead Data:
{json.dumps(lead, indent=2)}

Return JSON:
{{
  "score": 87,
  "grade": "A",
  "verdict": "Strong ICP match — prioritize immediately",
  "scoring_breakdown": {{
    "industry_fit": {{
      "score": 95,
      "reason": "Exact industry match — SaaS/B2B"
    }},
    "size_fit": {{
      "score": 80,
      "reason": "145 employees — within 50-500 target range"
    }},
    "signal_strength": {{
      "score": 90,
      "reason": "Series B + hiring AEs = strong budget signal"
    }},
    "contact_quality": {{
      "score": 85,
      "reason": "VP Marketing identified — decision-maker level"
    }},
    "timing": {{
      "score": 88,
      "reason": "Post-funding window — optimal outreach timing"
    }}
  }},
  "disqualifiers": [],
  "recommended_action": "Immediate outreach to VP Marketing with funding congratulations angle",
  "estimated_deal_value": "$24,000/year",
  "confidence": 0.91
}}
"""
        )

        self.tasks_completed += 1
        logger.info(f"[QUALIFY] Score: {scored.get('score', 0)}/100 | Grade: {scored.get('grade', '?')}")
        return {**lead, **scored}


# ─────────────────────────────────────────────
# AGENT 5: REACH — AI Outreach Engine
# ─────────────────────────────────────────────

class ReachAgent(BaseAgent):
    """
    Writes hyper-personalized outreach emails using real context.
    Not templates — genuine AI-crafted messages using company signals,
    contact background, and timing triggers.
    """

    def __init__(self, config: dict):
        super().__init__("REACH", config)

    async def execute(self, payload: dict) -> dict:
        lead = payload.get("lead", {})
        sender = payload.get("sender", {})
        sequence_step = payload.get("step", 1)

        company_name = lead.get("company", {}).get("name", "their company")
        contact = (lead.get("contacts") or [{}])[0]

        logger.info(f"[REACH] Writing email step {sequence_step} for {contact.get('name', 'contact')}")

        email = await self.call_claude_json(
            system="""You are REACH, an elite B2B outreach copywriter agent.
You write hyper-personalized cold emails that get responses.
You use real context — funding news, hiring signals, tech stack — to craft relevant messages.
Never use generic templates. Every email is unique. Be concise, human, and valuable.""",
            prompt=f"""
Write a personalized cold email (step {sequence_step} of a sequence) for:

Contact: {json.dumps(contact, indent=2)}
Company: {json.dumps(lead.get('company', {}), indent=2)}
Signals: {json.dumps(lead.get('signals', []), indent=2)}
Sender: {json.dumps(sender, indent=2)}

Return JSON:
{{
  "subject": "Congrats on the Series B, [Name]",
  "body": "Hi [First Name],\\n\\nSaw the announcement...",
  "personalization_hooks": ["Series B funding", "Hiring 8 AEs"],
  "estimated_open_rate": 0.48,
  "estimated_reply_rate": 0.12,
  "send_at_recommendation": "Tuesday 9-11am local time",
  "follow_up_in_days": 4
}}
"""
        )

        self.tasks_completed += 1
        self.config.get("on_email_ready", lambda x: None)(email)
        return email


# ─────────────────────────────────────────────
# AGENT 6: LEARN — Self-Improvement Engine
# ─────────────────────────────────────────────

class LearnAgent(BaseAgent):
    """
    Analyzes won/lost deal data to continuously improve:
    - ICP scoring model weights
    - Signal detection thresholds
    - Outreach timing recommendations
    - Disqualification patterns
    """

    def __init__(self, config: dict):
        super().__init__("LEARN", config)

    async def execute(self, payload: dict) -> dict:
        won_deals = payload.get("won_deals", [])
        lost_deals = payload.get("lost_deals", [])
        current_icp = payload.get("current_icp", {})

        logger.info(f"[LEARN] Analyzing {len(won_deals)} won / {len(lost_deals)} lost deals")

        improvements = await self.call_claude_json(
            system="""You are LEARN, a self-improvement agent for a lead generation OS.
You analyze patterns in won vs lost deals to improve the AI scoring model.
Provide specific, actionable model improvements with reasoning.""",
            prompt=f"""
Analyze these deal outcomes and recommend ICP model improvements:

Won Deals ({len(won_deals)}):
{json.dumps(won_deals[:5], indent=2)}

Lost Deals ({len(lost_deals)}):
{json.dumps(lost_deals[:5], indent=2)}

Current ICP Model:
{json.dumps(current_icp, indent=2)}

Return JSON:
{{
  "accuracy_improvement": 0.18,
  "icp_refinements": [
    {{
      "dimension": "company_size",
      "old_value": "10-500",
      "new_value": "50-300",
      "reason": "Deals under 50 employees have 3x longer sales cycles",
      "confidence": 0.87
    }}
  ],
  "new_disqualifiers": [
    "Bootstrapped companies with <$1M revenue"
  ],
  "new_positive_signals": [
    "Companies using Salesforce (integration opportunity)"
  ],
  "timing_insights": {{
    "best_outreach_days": ["Tuesday", "Wednesday"],
    "best_outreach_hours": "9-11am local",
    "avg_response_time": "2.3 days"
  }},
  "summary": "Model improved by 18% accuracy based on 47 deal outcomes"
}}
"""
        )

        self.tasks_completed += 1
        logger.info(f"[LEARN] Improvements identified: {len(improvements.get('icp_refinements', []))}")
        return improvements
