"""
LeadOS Core Data Models
All shared data structures across the agent system.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4


# ── Enums ────────────────────────────────────────────────────────────────────

class LeadStatus(str, Enum):
    NEW = "new"
    ENRICHED = "enriched"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    CONVERTED = "converted"


class LeadSource(str, Enum):
    WEB_CRAWLER = "web_crawler"
    LINKEDIN = "linkedin"
    JOB_BOARDS = "job_boards"
    SOCIAL_SIGNALS = "social_signals"
    INBOUND = "inbound"
    MANUAL = "manual"
    CRM_IMPORT = "crm_import"


class AgentTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class AgentType(str, Enum):
    CRAWLER = "crawler"
    LINKEDIN = "linkedin"
    ENRICHER = "enricher"
    QUALIFIER = "qualifier"
    EMAIL_VERIFIER = "email_verifier"
    OUTREACH = "outreach"
    CRM_SYNC = "crm_sync"
    SIGNAL_DETECTOR = "signal_detector"


# ── Core Models ───────────────────────────────────────────────────────────────

@dataclass
class Company:
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    domain: str = ""
    industry: str = ""
    employee_count: Optional[int] = None
    annual_revenue: Optional[str] = None
    location: str = ""
    description: str = ""
    linkedin_url: Optional[str] = None
    technologies: List[str] = field(default_factory=list)
    funding_stage: Optional[str] = None
    funding_amount: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    enriched_at: Optional[datetime] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Lead:
    id: str = field(default_factory=lambda: str(uuid4()))
    
    # Identity
    first_name: str = ""
    last_name: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    title: str = ""
    linkedin_url: Optional[str] = None
    
    # Company
    company: Optional[Company] = None
    company_name: str = ""
    
    # LeadOS Intelligence
    source: LeadSource = LeadSource.WEB_CRAWLER
    status: LeadStatus = LeadStatus.NEW
    ai_score: Optional[int] = None              # 0–100 ICP match score
    ai_score_reasoning: Optional[str] = None    # Why this score was given
    icp_match: Optional[float] = None           # 0.0–1.0
    intent_signals: List[str] = field(default_factory=list)  # e.g. ["hiring", "raised funding"]
    
    # Email
    email_verified: Optional[bool] = None
    email_deliverability: Optional[str] = None  # "valid", "risky", "invalid"
    
    # CRM sync tracking
    hubspot_id: Optional[str] = None
    salesforce_id: Optional[str] = None
    pipedrive_id: Optional[str] = None
    crm_synced_at: Optional[datetime] = None
    
    # Outreach
    outreach_sequence_id: Optional[str] = None
    last_contacted_at: Optional[datetime] = None
    reply_received: bool = False
    
    # Meta
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_qualified(self) -> bool:
        return self.ai_score is not None and self.ai_score >= 70

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "title": self.title,
            "company": self.company_name or (self.company.name if self.company else ""),
            "source": self.source.value,
            "status": self.status.value,
            "ai_score": self.ai_score,
            "ai_score_reasoning": self.ai_score_reasoning,
            "intent_signals": self.intent_signals,
            "email_verified": self.email_verified,
            "linkedin_url": self.linkedin_url,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AgentTask:
    id: str = field(default_factory=lambda: str(uuid4()))
    agent_type: AgentType = AgentType.CRAWLER
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    lead_id: Optional[str] = None


@dataclass
class ICPProfile:
    """Ideal Customer Profile — used by the Qualifier Agent to score leads."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "Default ICP"
    
    # Target company criteria
    target_industries: List[str] = field(default_factory=list)
    min_employees: Optional[int] = None
    max_employees: Optional[int] = None
    min_revenue: Optional[str] = None
    target_geographies: List[str] = field(default_factory=list)
    required_technologies: List[str] = field(default_factory=list)
    
    # Target persona criteria
    target_titles: List[str] = field(default_factory=list)
    target_seniority: List[str] = field(default_factory=list)   # e.g. ["VP", "Director", "C-Suite"]
    
    # Positive signals (boost score)
    positive_signals: List[str] = field(default_factory=lambda: [
        "recently raised funding",
        "hiring sales or marketing roles",
        "product launch announced",
        "new leadership hired",
        "expanding to new markets",
    ])
    
    # Negative signals (reduce score)
    negative_signals: List[str] = field(default_factory=lambda: [
        "company downsizing",
        "recent layoffs",
        "acquisition completed",
        "company shutting down",
    ])
    
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SyncRecord:
    """Tracks every CRM push/pull operation."""
    id: str = field(default_factory=lambda: str(uuid4()))
    crm: str = ""                               # "hubspot", "salesforce", "pipedrive"
    operation: str = ""                         # "push", "pull", "update", "dedup"
    lead_id: Optional[str] = None
    crm_record_id: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    records_affected: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
