"""
LeadOS Qualifier Agent
The most important agent: uses Claude AI to score leads against your ICP.
This is the intelligence layer that separates LeadOS from traditional lead gen tools.
"""

import json
import logging
from typing import Dict, Any

import anthropic

from agents.base_agent import BaseAgent
from core.models import AgentTask, Lead, LeadStatus

log = logging.getLogger("LeadOS.QualifierAgent")


QUALIFIER_SYSTEM_PROMPT = """You are LeadOS's AI Lead Qualification Engine.

Your job: score a lead (0–100) based on how well they match an Ideal Customer Profile (ICP).

You will receive:
1. The lead's data (name, title, company, industry, signals, etc.)
2. The ICP definition (target industries, titles, company size, signals)

You must return ONLY valid JSON in this exact format:
{
  "score": <integer 0-100>,
  "reasoning": "<2-3 sentence explanation of why this score was given>",
  "positive_factors": ["<factor1>", "<factor2>"],
  "negative_factors": ["<factor1>", "<factor2>"],
  "recommended_action": "<one of: push_to_crm | nurture | disqualify | needs_more_data>"
}

Scoring rubric:
- 85–100: Perfect ICP match. Push to CRM immediately.
- 70–84:  Strong match. Push to CRM with high priority.
- 50–69:  Partial match. Add to nurture sequence.
- 30–49:  Weak match. Low priority, monitor only.
- 0–29:   No match. Disqualify.

Be precise. Be honest. Do not inflate scores. A bad lead pushed to a CRM wastes a salesperson's time.
"""


class QualifierAgent(BaseAgent):
    """
    Uses Claude AI to qualify leads against the ICP profile.
    
    This agent is the competitive moat of LeadOS — it replaces the 
    guesswork of traditional lead qualification with AI reasoning
    that learns from your specific ICP and past performance.
    """

    def __init__(self, config, orchestrator):
        super().__init__(config, orchestrator)
        self.client = None

    async def initialize(self):
        if not self.config.anthropic_api_key:
            log.warning("No ANTHROPIC_API_KEY set. Qualifier will use rule-based fallback.")
            return
        self.client = anthropic.AsyncAnthropic(api_key=self.config.anthropic_api_key)
        log.info("Qualifier Agent connected to Claude AI.")

    async def execute(self, task: AgentTask) -> Dict[str, Any]:
        lead_id = task.payload.get("lead_id")
        lead = self.get_lead(lead_id)

        if not lead:
            raise ValueError(f"Lead {lead_id} not found in DB")

        log.info(f"Qualifying: {lead.full_name} @ {lead.company_name}")

        if self.client:
            result = await self._ai_qualify(lead)
        else:
            result = self._rule_based_qualify(lead)

        # Update lead with AI score
        lead.ai_score = result["score"]
        lead.ai_score_reasoning = result["reasoning"]
        lead.status = (
            LeadStatus.QUALIFIED
            if result["score"] >= self.config.min_qualify_score
            else LeadStatus.DISQUALIFIED
        )
        self.save_lead(lead)

        log.info(
            f"  Score: {result['score']}/100 | {lead.status.value} | "
            f"Action: {result.get('recommended_action')}"
        )

        return {
            "lead_id": lead_id,
            "score": result["score"],
            "status": lead.status.value,
            "recommended_action": result.get("recommended_action"),
        }

    async def _ai_qualify(self, lead: Lead) -> Dict:
        """Use Claude to score the lead."""
        icp = self.icp

        user_message = f"""
LEAD DATA:
- Name: {lead.full_name}
- Title: {lead.title}
- Company: {lead.company_name}
- Industry: {lead.company.industry if lead.company else "Unknown"}
- Employees: {lead.company.employee_count if lead.company else "Unknown"}
- Email Verified: {lead.email_verified}
- Intent Signals: {", ".join(lead.intent_signals) if lead.intent_signals else "None detected"}
- LinkedIn: {"Yes" if lead.linkedin_url else "No"}
- Source: {lead.source.value}

ICP DEFINITION:
- Target Industries: {", ".join(icp.target_industries) if icp else "SaaS, Tech"}
- Target Titles: {", ".join(icp.target_titles) if icp else "VP, Director, C-Suite"}
- Company Size: {icp.min_employees}–{icp.max_employees} employees
- Positive Signals: {", ".join(icp.positive_signals) if icp else "hiring, funding"}
- Negative Signals: {", ".join(icp.negative_signals) if icp else "layoffs, shutdown"}

Score this lead now.
"""

        response = await self.client.messages.create(
            model=self.config.llm_model,
            max_tokens=512,
            system=QUALIFIER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        return json.loads(raw)

    def _rule_based_qualify(self, lead: Lead) -> Dict:
        """
        Fallback scoring when no API key is set.
        Uses heuristic rules instead of Claude.
        """
        score = 40  # baseline

        # Title match
        if self.icp and lead.title:
            for title in self.icp.target_titles:
                if title.lower() in lead.title.lower():
                    score += 20
                    break

        # Company size match
        if self.icp and lead.company and lead.company.employee_count:
            emp = lead.company.employee_count
            if self.icp.min_employees <= emp <= self.icp.max_employees:
                score += 15

        # Email verified
        if lead.email_verified:
            score += 10

        # Intent signals
        if lead.intent_signals:
            score += min(len(lead.intent_signals) * 5, 15)

        score = max(0, min(100, score))

        return {
            "score": score,
            "reasoning": f"Rule-based score. Title match and signal presence evaluated. Score: {score}/100.",
            "positive_factors": lead.intent_signals[:2],
            "negative_factors": [],
            "recommended_action": "push_to_crm" if score >= 70 else "nurture",
        }
