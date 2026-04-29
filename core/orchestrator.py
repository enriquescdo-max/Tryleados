"""
LeadOS Agent Orchestrator
The central brain that spawns, manages, and coordinates all AI agents.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from core.config import LeadOSConfig
from core.models import AgentTask, AgentType, AgentTaskStatus, Lead, ICPProfile, LeadStatus

log = logging.getLogger("LeadOS.Orchestrator")


class AgentOrchestrator:
    """
    The Orchestrator is the central command layer of LeadOS.

    It manages a pool of specialized AI agents and coordinates them
    through a task queue. Each lead flows through a pipeline:

        Discover → Enrich → Verify → Qualify → Sync → (Outreach)

    Agents are fully async, run concurrently, and self-report status
    back to the orchestrator for monitoring and retry logic.
    """

    def __init__(self, config: LeadOSConfig):
        self.config = config
        self.agents: Dict[AgentType, object] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.active_tasks: Dict[str, AgentTask] = {}
        self.leads_db: Dict[str, Lead] = {}
        self.icp_profile: Optional[ICPProfile] = None
        self.event_log: List[Dict] = []
        self._running = False

    async def initialize(self):
        """Instantiate and initialize all agents."""
        log.info("Initializing agent pool...")

        # Boot Supabase and reload any leads that survived a previous run
        from db import supabase_client
        supabase_client.init(self.config.supabase_url, self.config.supabase_service_key)
        if supabase_client.is_ready():
            await self._load_leads_from_supabase(supabase_client)
        # Agents are imported lazily to avoid circular imports
        from agents.crawler_agent import CrawlerAgent
        from agents.linkedin_agent import LinkedInAgent
        from agents.enricher_agent import EnricherAgent
        from agents.qualifier_agent import QualifierAgent
        from agents.email_verifier_agent import EmailVerifierAgent
        from agents.signal_detector_agent import SignalDetectorAgent
        from agents.crm_sync_agent import CRMSyncAgent
        from agents.outreach_agent import OutreachAgent

        self.agents = {
            AgentType.CRAWLER:         CrawlerAgent(self.config, self),
            AgentType.LINKEDIN:        LinkedInAgent(self.config, self),
            AgentType.ENRICHER:        EnricherAgent(self.config, self),
            AgentType.EMAIL_VERIFIER:  EmailVerifierAgent(self.config, self),
            AgentType.QUALIFIER:       QualifierAgent(self.config, self),
            AgentType.SIGNAL_DETECTOR: SignalDetectorAgent(self.config, self),
            AgentType.CRM_SYNC:        CRMSyncAgent(self.config, self),
            AgentType.OUTREACH:        OutreachAgent(self.config, self),
        }

        for agent_type, agent in self.agents.items():
            await agent.initialize()
            log.info(f"  ✅ {agent_type.value} agent ready")

        self.icp_profile = self._default_icp()
        log.info(f"ICP profile loaded: {self.icp_profile.name}")

    async def run_forever(self):
        """Main agent loop."""
        self._running = True
        log.info("Orchestrator loop started.")

        workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.config.max_concurrent_agents)
        ]
        await self._seed_discovery_tasks()
        await asyncio.gather(*workers)

    async def _worker(self, worker_id: int):
        while self._running:
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=5.0)
                await self._dispatch_task(task, worker_id)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                log.error(f"Worker {worker_id} error: {e}")

    async def _dispatch_task(self, task: AgentTask, worker_id: int):
        agent = self.agents.get(task.agent_type)
        if not agent:
            return

        task.status = AgentTaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        self.active_tasks[task.id] = task
        log.info(f"[Worker {worker_id}] {task.agent_type.value} → {task.payload.get('target', task.id[:8])}")

        try:
            result = await agent.execute(task)
            task.status = AgentTaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.utcnow()
            self._log_event(task.agent_type.value, f"Completed: {task.payload.get('target', '')}", "success")
            await self._chain_next_task(task, result)

        except Exception as e:
            log.error(f"Task {task.id} failed: {e}")
            task.status = AgentTaskStatus.FAILED
            task.error = str(e)
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = AgentTaskStatus.RETRYING
                await asyncio.sleep(2 ** task.retry_count)
                await self.task_queue.put(task)
        finally:
            self.active_tasks.pop(task.id, None)
            self.task_queue.task_done()

    async def _chain_next_task(self, completed_task: AgentTask, result: Dict):
        """Auto-chain the lead pipeline."""
        lead_id = result.get("lead_id") or completed_task.lead_id
        if not lead_id:
            return

        next_steps = {
            AgentType.CRAWLER:         AgentType.ENRICHER,
            AgentType.LINKEDIN:        AgentType.ENRICHER,
            AgentType.ENRICHER:        AgentType.EMAIL_VERIFIER,
            AgentType.EMAIL_VERIFIER:  AgentType.SIGNAL_DETECTOR,
            AgentType.SIGNAL_DETECTOR: AgentType.QUALIFIER,
            AgentType.QUALIFIER:       AgentType.CRM_SYNC,
        }

        next_type = next_steps.get(completed_task.agent_type)

        if completed_task.agent_type == AgentType.QUALIFIER:
            lead = self.leads_db.get(lead_id)
            if not lead or not lead.is_qualified:
                log.info(f"Lead {lead_id} below threshold. Skipping CRM sync.")
                return

        if next_type:
            await self._enqueue(next_type, {"lead_id": lead_id}, lead_id)

        if next_type == AgentType.CRM_SYNC and self.config.enable_auto_outreach:
            await self._enqueue(AgentType.OUTREACH, {"lead_id": lead_id}, lead_id)

    async def _enqueue(self, agent_type: AgentType, payload: Dict, lead_id: Optional[str] = None):
        task = AgentTask(agent_type=agent_type, payload=payload, lead_id=lead_id)
        await self.task_queue.put(task)
        return task

    async def _seed_discovery_tasks(self):
        log.info("Seeding initial discovery tasks...")
        if self.config.enable_web_crawler:
            for url in ["https://www.g2.com/categories/crm", "https://www.ycombinator.com/companies"]:
                await self._enqueue(AgentType.CRAWLER, {"url": url, "target": url})
        if self.config.enable_linkedin_intel:
            await self._enqueue(AgentType.LINKEDIN, {"search_query": "VP Sales SaaS", "target": "LinkedIn search"})

    async def submit_lead_data(self, lead: Lead) -> str:
        self.leads_db[lead.id] = lead
        await self._enqueue(AgentType.ENRICHER, {"lead_id": lead.id}, lead.id)
        return lead.id

    async def run_campaign(self, campaign: Dict) -> List[AgentTask]:
        log.info(f"Campaign: {campaign.get('prompt')}")
        tasks = []
        for source in campaign.get("sources", ["crawler"]):
            agent_type = AgentType.CRAWLER if source == "crawler" else AgentType.LINKEDIN
            task = await self._enqueue(agent_type, {
                "campaign": True,
                "prompt": campaign["prompt"],
                "max_leads": campaign.get("max_leads", 50),
                "target": f"Campaign: {campaign['prompt'][:50]}",
            })
            tasks.append(task)
        return tasks

    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "queue_size": self.task_queue.qsize(),
            "active_tasks": len(self.active_tasks),
            "total_leads": len(self.leads_db),
            "qualified_leads": sum(1 for l in self.leads_db.values() if l.is_qualified),
            "agents": {k.value: "active" for k in self.agents},
            "recent_events": self.event_log[-20:],
        }

    def update_icp(self, icp: ICPProfile):
        self.icp_profile = icp
        log.info(f"ICP updated: {icp.name}")

    def _log_event(self, agent: str, message: str, level: str = "info"):
        self.event_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent, "message": message, "level": level,
        })
        if len(self.event_log) > 1000:
            self.event_log = self.event_log[-500:]

    async def _load_leads_from_supabase(self, supabase_client) -> None:
        """Restore in-memory leads_db from Supabase on startup."""
        import asyncio
        rows = await asyncio.to_thread(supabase_client.load_leads)
        for row in rows:
            lead = Lead(
                id=row["id"],
                first_name=(row.get("name") or "").split(" ")[0],
                last_name=" ".join((row.get("name") or "").split(" ")[1:]),
                email=row.get("email"),
                phone=row.get("phone"),
                title=row.get("title", ""),
                company_name=row.get("company", ""),
                intent_signals=row.get("intent_signals") or [],
                email_verified=row.get("email_verified"),
                linkedin_url=row.get("linkedin_url"),
                ai_score=row.get("ai_score"),
                ai_score_reasoning=row.get("ai_score_reasoning"),
            )
            # Restore status
            try:
                lead.status = LeadStatus(row.get("status", "new"))
            except (ValueError, NameError, Exception):
                pass
            # Restore source
            try:
                from core.models import LeadSource
                lead.source = LeadSource(row.get("source", "web_crawler"))
            except ValueError:
                pass
            self.leads_db[lead.id] = lead
        log.info(f"Restored {len(rows)} leads from Supabase into memory.")

    def _default_icp(self) -> ICPProfile:
        return ICPProfile(
            name="Default SaaS ICP",
            target_industries=["SaaS", "Technology", "FinTech"],
            min_employees=10, max_employees=500,
            target_titles=["CEO", "CTO", "CMO", "VP Sales", "Founder"],
            target_seniority=["C-Suite", "VP", "Director"],
        )
