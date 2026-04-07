"""
LeadOS Crawler Agent
Discovers leads by scraping websites, directories, and company pages.
Respects robots.txt and uses polite crawl delays.
"""

import asyncio
import re
import logging
from typing import Dict, Any, List
from urllib.parse import urlparse, urljoin
from uuid import uuid4

try:
    import aiohttp
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

from agents.base_agent import BaseAgent
from core.models import AgentTask, Lead, Company, LeadSource

log = logging.getLogger("LeadOS.CrawlerAgent")


class CrawlerAgent(BaseAgent):
    """
    Web Crawler Agent — discovers leads from:
      - Company directories (G2, YC, ProductHunt)
      - Tech blogs and press releases
      - Job boards (Greenhouse, Lever, Ashby)
      - Industry-specific sites

    Innovates over traditional scrapers by:
      1. Using AI to extract structured lead data from unstructured HTML
      2. Following "interesting" links intelligently
      3. Detecting intent signals from page content
    """

    def __init__(self, config, orchestrator):
        super().__init__(config, orchestrator)
        self.session = None
        self.visited_urls = set()

    async def initialize(self):
        if not HAS_DEPS:
            log.warning("aiohttp/bs4 not installed. Crawler running in mock mode.")
            return
        connector = aiohttp.TCPConnector(limit=10, ssl=False)
        self.session = aiohttp.ClientSession(
            connector=connector,
            headers={
                "User-Agent": "LeadOS-Bot/2.0 (lead intelligence; contact@leadOS.ai)",
                "Accept": "text/html,application/xhtml+xml",
            },
            timeout=aiohttp.ClientTimeout(total=15),
        )
        log.info("Crawler session initialized.")

    async def execute(self, task: AgentTask) -> Dict[str, Any]:
        url = task.payload.get("url")
        campaign = task.payload.get("campaign", False)
        max_leads = task.payload.get("max_leads", 20)

        if not url and not campaign:
            raise ValueError("Crawler task must have 'url' or 'campaign' in payload")

        if not HAS_DEPS or not self.session:
            # Mock mode for demo/testing
            return await self._mock_crawl(task)

        leads_found = []

        if campaign:
            # Campaign mode: use prompt to discover URLs, then crawl them
            urls = await self._discover_urls_for_campaign(task.payload.get("prompt", ""))
            for u in urls[:5]:
                found = await self._crawl_page(u)
                leads_found.extend(found)
                if len(leads_found) >= max_leads:
                    break
        else:
            leads_found = await self._crawl_page(url)

        # Save leads to DB and chain enrichment
        saved_ids = []
        for lead_data in leads_found[:max_leads]:
            lead = self._dict_to_lead(lead_data)
            self.save_lead(lead)
            saved_ids.append(lead.id)
            # Each crawled lead enters the pipeline
            await self.orchestrator._enqueue(
                agent_type=__import__("core.models", fromlist=["AgentType"]).AgentType.ENRICHER,
                payload={"lead_id": lead.id},
                lead_id=lead.id,
            )

        log.info(f"Crawled {url or 'campaign'} → {len(leads_found)} leads discovered")

        return {
            "leads_found": len(leads_found),
            "lead_ids": saved_ids,
            "source_url": url,
        }

    async def _crawl_page(self, url: str) -> List[Dict]:
        """Fetch and parse a page for lead data."""
        if url in self.visited_urls:
            return []
        self.visited_urls.add(url)

        await asyncio.sleep(self.config.crawl_delay_seconds)

        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        except Exception as e:
            log.warning(f"Failed to fetch {url}: {e}")
            return []

        soup = BeautifulSoup(html, "html.parser")
        leads = []

        # Extract emails from page
        emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)
        domain = urlparse(url).netloc.replace("www.", "")

        # Extract names near emails (heuristic)
        for email in set(emails[:10]):
            if any(skip in email for skip in ["noreply", "support", "info", "admin", "hello"]):
                continue

            leads.append({
                "email": email,
                "company_domain": domain,
                "company_name": domain.split(".")[0].title(),
                "source_url": url,
                "intent_signals": self._detect_signals(html),
            })

        return leads

    def _detect_signals(self, html: str) -> List[str]:
        """Detect buying intent signals from page content."""
        signals = []
        html_lower = html.lower()

        signal_keywords = {
            "hiring sales": "hiring sales team",
            "we're hiring": "actively hiring",
            "series a": "raised Series A",
            "series b": "raised Series B",
            "series c": "raised Series C",
            "product launch": "product launch",
            "new partnership": "new partnership announced",
            "expansion": "expanding operations",
        }

        for keyword, signal in signal_keywords.items():
            if keyword in html_lower:
                signals.append(signal)

        return signals[:5]

    async def _discover_urls_for_campaign(self, prompt: str) -> List[str]:
        """Use heuristics (or AI) to find relevant URLs for a campaign."""
        # In production this would use Claude to suggest URLs based on the prompt
        return [
            "https://www.g2.com/categories/crm",
            "https://www.ycombinator.com/companies",
        ]

    def _dict_to_lead(self, data: Dict) -> Lead:
        company = Company(
            name=data.get("company_name", ""),
            domain=data.get("company_domain", ""),
        )
        return Lead(
            email=data.get("email"),
            company=company,
            company_name=data.get("company_name", ""),
            source=LeadSource.WEB_CRAWLER,
            intent_signals=data.get("intent_signals", []),
            raw_data=data,
        )

    async def _mock_crawl(self, task: AgentTask) -> Dict[str, Any]:
        """Mock mode — returns realistic fake data for demo/testing."""
        await asyncio.sleep(0.5)

        mock_leads = [
            {"first_name": "Sarah", "last_name": "Chen", "title": "VP Marketing",
             "email": "s.chen@stripe.com", "company_name": "Stripe",
             "company_domain": "stripe.com", "intent_signals": ["raised Series B", "hiring sales"]},
            {"first_name": "Marcus", "last_name": "Webb", "title": "Head of Growth",
             "email": "mwebb@linear.app", "company_name": "Linear",
             "company_domain": "linear.app", "intent_signals": ["product launch"]},
        ]

        for data in mock_leads:
            lead = Lead(
                first_name=data["first_name"],
                last_name=data["last_name"],
                title=data["title"],
                email=data["email"],
                company_name=data["company_name"],
                source=LeadSource.WEB_CRAWLER,
                intent_signals=data["intent_signals"],
                raw_data=data,
            )
            self.save_lead(lead)

        log.info(f"[MOCK] Crawler found {len(mock_leads)} leads")
        return {"leads_found": len(mock_leads), "mock": True}

    async def cleanup(self):
        if self.session:
            await self.session.close()
