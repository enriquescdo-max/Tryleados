"""
LeadOS Configuration
All settings loaded from environment variables or .env file.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LeadOSConfig:
    # ── AI / LLM ─────────────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-4-5"
    llm_max_tokens: int = 4096

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql://leadOS:password@localhost:5432/leadOS"
    redis_url: str = "redis://localhost:6379/0"
    supabase_url: str = ""
    supabase_service_key: str = ""

    # ── CRM Integrations ──────────────────────────────────────────────────────
    hubspot_api_key: Optional[str] = None
    salesforce_client_id: Optional[str] = None
    salesforce_client_secret: Optional[str] = None
    salesforce_instance_url: Optional[str] = None
    pipedrive_api_key: Optional[str] = None
    ghl_api_key: Optional[str] = None

    # ── Enrichment APIs ───────────────────────────────────────────────────────
    hunter_api_key: Optional[str] = None        # Email finding
    apollo_api_key: Optional[str] = None        # B2B data enrichment
    clearbit_api_key: Optional[str] = None      # Company enrichment
    linkedin_cookie: Optional[str] = None       # LinkedIn scraping session

    # ── Agent Behavior ────────────────────────────────────────────────────────
    min_qualify_score: int = 70                 # Minimum AI score to push to CRM
    max_concurrent_agents: int = 10
    crawl_delay_seconds: float = 1.5           # Polite crawl delay
    agent_loop_interval_seconds: int = 60

    # ── Outreach ──────────────────────────────────────────────────────────────
    sendgrid_api_key: Optional[str] = None
    outreach_from_email: str = "leads@yourdomain.com"
    outreach_from_name: str = "LeadOS"

    # ── Feature Flags ─────────────────────────────────────────────────────────
    enable_web_crawler: bool = True
    enable_linkedin_intel: bool = True
    enable_email_verifier: bool = True
    enable_auto_qualify: bool = True
    enable_auto_outreach: bool = False          # Off by default — needs approval

    @classmethod
    def from_env(cls) -> "LeadOSConfig":
        """Load config from environment variables."""
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            llm_model=os.getenv("LEADOS_LLM_MODEL", "claude-opus-4-5"),
            database_url=os.getenv("DATABASE_URL", "postgresql://leadOS:password@localhost:5432/leadOS"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            hubspot_api_key=os.getenv("HUBSPOT_API_KEY"),
            salesforce_client_id=os.getenv("SALESFORCE_CLIENT_ID"),
            salesforce_client_secret=os.getenv("SALESFORCE_CLIENT_SECRET"),
            salesforce_instance_url=os.getenv("SALESFORCE_INSTANCE_URL"),
            pipedrive_api_key=os.getenv("PIPEDRIVE_API_KEY"),
            ghl_api_key=os.getenv("GHL_API_KEY"),
            hunter_api_key=os.getenv("HUNTER_API_KEY"),
            apollo_api_key=os.getenv("APOLLO_API_KEY"),
            clearbit_api_key=os.getenv("CLEARBIT_API_KEY"),
            linkedin_cookie=os.getenv("LINKEDIN_SESSION_COOKIE"),
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_service_key=os.getenv("SUPABASE_SERVICE_KEY", ""),
            sendgrid_api_key=os.getenv("SENDGRID_API_KEY"),
            min_qualify_score=int(os.getenv("MIN_QUALIFY_SCORE", "70")),
            max_concurrent_agents=int(os.getenv("MAX_CONCURRENT_AGENTS", "10")),
            enable_auto_outreach=os.getenv("ENABLE_AUTO_OUTREACH", "false").lower() == "true",
        )
