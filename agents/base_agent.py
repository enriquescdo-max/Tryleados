"""
LeadOS Base Agent
All agents inherit from this class.
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Dict, Any

from core.config import LeadOSConfig
from core.models import AgentTask

if TYPE_CHECKING:
    from core.orchestrator import AgentOrchestrator


class BaseAgent(ABC):
    """
    Abstract base for all LeadOS agents.
    
    Each agent has:
      - initialize(): async setup (HTTP sessions, API auth, etc.)
      - execute(task): the main work method
      - A reference to the orchestrator for accessing shared state
    """

    def __init__(self, config: LeadOSConfig, orchestrator: "AgentOrchestrator"):
        self.config = config
        self.orchestrator = orchestrator
        self.log = logging.getLogger(f"LeadOS.{self.__class__.__name__}")

    async def initialize(self):
        """Override to do async setup (open connections, auth, etc.)"""
        pass

    @abstractmethod
    async def execute(self, task: AgentTask) -> Dict[str, Any]:
        """
        Execute the agent's task.
        
        Args:
            task: The AgentTask containing payload and metadata.
            
        Returns:
            A dict with at minimum {"lead_id": str} so the
            orchestrator can chain the next pipeline step.
        """
        ...

    def get_lead(self, lead_id: str):
        """Convenience: fetch a lead from the shared DB."""
        return self.orchestrator.leads_db.get(lead_id)

    def save_lead(self, lead):
        """Upsert a lead into in-memory DB and persist to Supabase."""
        self.orchestrator.leads_db[lead.id] = lead
        try:
            from db import supabase_client
            supabase_client.save_lead(lead.to_dict())
        except Exception as e:
            self.log.warning(f"Supabase persist failed for lead {lead.id}: {e}")
        return lead

    @property
    def icp(self):
        return self.orchestrator.icp_profile
