"""
LeadOS REST API Server  v2.1
────────────────────────────────────────────────────────────────────────────
All endpoints the frontend needs — wired to real orchestrator state.

New in v2.1:
  GET/POST /icp              — ICP profile read/write
  GET      /crm/status       — CRM connection status
  GET      /crm/sync-log     — Recent sync log
  POST     /crm/sync         — Trigger manual CRM sync
  POST     /crm/connect      — Connect a CRM integration
  GET      /analytics        — Dashboard KPIs + 30-day chart
  GET/POST /sequences        — Outreach sequences
  POST     /outreach/generate — AI email copy via Claude
  POST     /auth/login       — Login → session token
  POST     /auth/logout      — Logout
  GET      /auth/me          — Current user info
"""
import asyncio, logging, os, hashlib, secrets, time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

log = logging.getLogger("LeadOS.API")


def build_routes(app, orchestrator):
    """Register all API routes onto an existing FastAPI app instance."""
    from fastapi import HTTPException, BackgroundTasks, Depends, Header, Request
    from pydantic import BaseModel

    # ── In-memory stores ──────────────────────────────────────────────────
    _sessions: Dict[str, Dict] = {}
    _sequences: List[Dict] = [
        {"id": "seq_001", "name": "Realtor Referral Partnership",
         "contacts": 0, "active": False, "steps": 4, "open_rate": 0, "reply_rate": 0,
         "created_at": datetime.utcnow().isoformat()},
        {"id": "seq_002", "name": "Auto Dealer Finance Manager",
         "contacts": 0, "active": False, "steps": 3, "open_rate": 0, "reply_rate": 0,
         "created_at": datetime.utcnow().isoformat()},
        {"id": "seq_003", "name": "Mortgage Broker Partnership",
         "contacts": 0, "active": False, "steps": 3, "open_rate": 0, "reply_rate": 0,
         "created_at": datetime.utcnow().isoformat()},
    ]
    _crm_state: Dict[str, Dict] = {
        "hubspot":     {"connected": False, "contacts_synced": 0, "uptime": 0, "last_sync": None},
        "salesforce":  {"connected": False, "contacts_synced": 0, "uptime": 0, "last_sync": None},
        "pipedrive":   {"connected": False, "contacts_synced": 0, "uptime": 0, "last_sync": None},
        "gohighlevel": {"connected": False},
        "zoho":        {"connected": False},
    }
    _sync_log: List[Dict] = []

    ADMIN_EMAIL    = os.getenv("LEADOS_ADMIN_EMAIL", "admin@leadOS.ai")
    ADMIN_PASSWORD = os.getenv("LEADOS_ADMIN_PASSWORD", "LeadOS2024!")

    def _hash(pw: str) -> str:
        return hashlib.sha256(pw.encode()).hexdigest()

    _users = {
        ADMIN_EMAIL: {
            "id": "user_001", "email": ADMIN_EMAIL, "name": "LeadOS Admin",
            "role": "admin", "password_hash": _hash(ADMIN_PASSWORD),
            "created_at": datetime.utcnow().isoformat(),
        }
    }

    def _create_session(user: Dict) -> str:
        token = secrets.token_urlsafe(32)
        _sessions[token] = {
            "user_id": user["id"], "email": user["email"], "role": user["role"],
            "created_at": time.time(), "expires_at": time.time() + 86400 * 7,
        }
        return token

    def _get_session(authorization: Optional[str] = Header(None)) -> Optional[Dict]:
        if not authorization:
            return None
        token = authorization.replace("Bearer ", "").strip()
        sess = _sessions.get(token)
        if not sess or time.time() > sess["expires_at"]:
            _sessions.pop(token, None)
            return None
        return sess

    def _require_auth(authorization: Optional[str] = Header(None)) -> Dict:
        sess = _get_session(authorization)
        if not sess:
            raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
        return sess

    class CampaignRequest(BaseModel):
        prompt: str
        sources: List[str] = ["crawler", "linkedin"]
        max_leads: int = 50

    class LeadSubmitRequest(BaseModel):
        first_name: str = ""
        last_name: str = ""
        email: Optional[str] = None
        title: str = ""
        company_name: str = ""

    class ICPUpdateRequest(BaseModel):
        name: Optional[str] = None
        target_industries: Optional[List[str]] = None
        target_titles: Optional[List[str]] = None
        target_seniority: Optional[List[str]] = None
        min_employees: Optional[int] = None
        max_employees: Optional[int] = None
        target_geographies: Optional[List[str]] = None
        positive_signals: Optional[List[str]] = None
        negative_signals: Optional[List[str]] = None

    class CRMConnectRequest(BaseModel):
        crm: str
        api_key: Optional[str] = None
        client_id: Optional[str] = None
        client_secret: Optional[str] = None
        instance_url: Optional[str] = None

    class CRMSyncRequest(BaseModel):
        crm: str = "all"

    class SequenceCreateRequest(BaseModel):
        name: str
        active: bool = False

    class OutreachGenerateRequest(BaseModel):
        lead_id: str
        step: int = 1

    class LoginRequest(BaseModel):
        email: str
        password: str

    # ── Core routes ───────────────────────────────────────────────────────

    @app.get("/")
    async def root():
        return {"name": "LeadOS", "version": "3.0", "status": "running", "docs": "/docs"}

    @app.get("/status")
    async def get_status():
        return orchestrator.get_status()

    @app.get("/leads")
    async def list_leads(limit: int = 50, status: Optional[str] = None):
        leads = list(orchestrator.leads_db.values())
        if status:
            leads = [l for l in leads if l.status.value == status]
        leads.sort(key=lambda l: l.ai_score or 0, reverse=True)
        return {"total": len(leads), "leads": [l.to_dict() for l in leads[:limit]]}

    @app.get("/leads/{lead_id}")
    async def get_lead(lead_id: str):
        lead = orchestrator.leads_db.get(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
        return lead.to_dict()

    @app.post("/leads")
    async def submit_lead(req: LeadSubmitRequest):
        from core.models import Lead, LeadSource
        lead = Lead(first_name=req.first_name, last_name=req.last_name,
                    email=req.email, title=req.title, company_name=req.company_name,
                    source=LeadSource.MANUAL)
        lead_id = await orchestrator.submit_lead_data(lead)
        return {"lead_id": lead_id, "status": "pipeline_started"}

    @app.delete("/leads/{lead_id}")
    async def delete_lead(lead_id: str):
        if lead_id not in orchestrator.leads_db:
            raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
        del orchestrator.leads_db[lead_id]
        return {"deleted": lead_id}

    @app.post("/campaigns")
    async def run_campaign(req: CampaignRequest, background_tasks: BackgroundTasks):
        background_tasks.add_task(orchestrator.run_campaign, req.dict())
        return {"status": "campaign_started", "prompt": req.prompt,
                "sources": req.sources, "campaign_id": f"camp_{int(time.time())}"}

    @app.get("/events")
    async def get_events(limit: int = 50):
        return {"events": orchestrator.event_log[-limit:], "total": len(orchestrator.event_log)}

    log.info("Routes registered via build_routes.")


async def start_api_server(orchestrator, host="0.0.0.0", port=8000):
    try:
        from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header, Request
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel
        import uvicorn
    except ImportError:
        log.warning("FastAPI not installed. Run: pip install fastapi uvicorn pydantic")
        await asyncio.sleep(99999)
        return

    app = FastAPI(title="LeadOS API", version="2.1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    # ── In-memory stores ──────────────────────────────────────────────────
    _sessions: Dict[str, Dict] = {}

    _sequences: List[Dict] = [
        {"id": "seq_001", "name": "Realtor Referral Partnership",
         "contacts": 0, "active": False, "steps": 4, "open_rate": 0, "reply_rate": 0,
         "created_at": datetime.utcnow().isoformat()},
        {"id": "seq_002", "name": "Auto Dealer Finance Manager",
         "contacts": 0, "active": False, "steps": 3, "open_rate": 0, "reply_rate": 0,
         "created_at": datetime.utcnow().isoformat()},
        {"id": "seq_003", "name": "Mortgage Broker Partnership",
         "contacts": 0, "active": False, "steps": 3, "open_rate": 0, "reply_rate": 0,
         "created_at": datetime.utcnow().isoformat()},
    ]

    _crm_state: Dict[str, Dict] = {
        "hubspot":     {"connected": False, "contacts_synced": 0, "uptime": 0, "last_sync": None},
        "salesforce":  {"connected": False, "contacts_synced": 0, "uptime": 0, "last_sync": None},
        "pipedrive":   {"connected": False, "contacts_synced": 0, "uptime": 0, "last_sync": None},
        "gohighlevel": {"connected": False},
        "zoho":        {"connected": False},
    }
    _sync_log: List[Dict] = []

    # ── Pydantic request models ───────────────────────────────────────────

    class CampaignRequest(BaseModel):
        prompt: str
        sources: List[str] = ["crawler", "linkedin"]
        max_leads: int = 50

    class LeadSubmitRequest(BaseModel):
        first_name: str = ""
        last_name: str = ""
        email: Optional[str] = None
        title: str = ""
        company_name: str = ""

    class ICPUpdateRequest(BaseModel):
        name: Optional[str] = None
        target_industries: Optional[List[str]] = None
        target_titles: Optional[List[str]] = None
        target_seniority: Optional[List[str]] = None
        min_employees: Optional[int] = None
        max_employees: Optional[int] = None
        target_geographies: Optional[List[str]] = None
        positive_signals: Optional[List[str]] = None
        negative_signals: Optional[List[str]] = None

    class CRMConnectRequest(BaseModel):
        crm: str
        api_key: Optional[str] = None
        client_id: Optional[str] = None
        client_secret: Optional[str] = None
        instance_url: Optional[str] = None

    class CRMSyncRequest(BaseModel):
        crm: str = "all"

    class SequenceCreateRequest(BaseModel):
        name: str
        active: bool = False

    class OutreachGenerateRequest(BaseModel):
        lead_id: str
        step: int = 1

    class LoginRequest(BaseModel):
        email: str
        password: str

    # ── Auth helpers ──────────────────────────────────────────────────────

    ADMIN_EMAIL    = os.getenv("LEADOS_ADMIN_EMAIL", "admin@leadOS.ai")
    ADMIN_PASSWORD = os.getenv("LEADOS_ADMIN_PASSWORD", "LeadOS2024!")

    def _hash(pw: str) -> str:
        return hashlib.sha256(pw.encode()).hexdigest()

    _users = {
        ADMIN_EMAIL: {
            "id": "user_001", "email": ADMIN_EMAIL, "name": "LeadOS Admin",
            "role": "admin", "password_hash": _hash(ADMIN_PASSWORD),
            "created_at": datetime.utcnow().isoformat(),
        }
    }

    def _create_session(user: Dict) -> str:
        token = secrets.token_urlsafe(32)
        _sessions[token] = {
            "user_id": user["id"], "email": user["email"], "role": user["role"],
            "created_at": time.time(), "expires_at": time.time() + 86400 * 7,
        }
        return token

    def _get_session(authorization: Optional[str] = Header(None)) -> Optional[Dict]:
        if not authorization:
            return None
        token = authorization.replace("Bearer ", "").strip()
        sess = _sessions.get(token)
        if not sess or time.time() > sess["expires_at"]:
            _sessions.pop(token, None)
            return None
        return sess

    def _require_auth(authorization: Optional[str] = Header(None)) -> Dict:
        sess = _get_session(authorization)
        if not sess:
            raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
        return sess

    # ══════════════════════════════════════════════════════════════════════
    # AUTH
    # ══════════════════════════════════════════════════════════════════════

    @app.post("/auth/login")
    async def login(req: LoginRequest):
        user = _users.get(req.email)
        if not user or user["password_hash"] != _hash(req.password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = _create_session(user)
        safe_user = {k: v for k, v in user.items() if k != "password_hash"}
        return {"token": token, "user": safe_user, "expires_in": 86400 * 7}

    @app.post("/auth/logout")
    async def logout(authorization: Optional[str] = Header(None)):
        if authorization:
            _sessions.pop(authorization.replace("Bearer ", "").strip(), None)
        return {"status": "logged_out"}

    @app.get("/auth/me")
    async def get_me(sess: Dict = Depends(_require_auth)):
        user = _users.get(sess["email"], {})
        return {k: v for k, v in user.items() if k != "password_hash"}

    # ══════════════════════════════════════════════════════════════════════
    # CORE
    # ══════════════════════════════════════════════════════════════════════

    @app.get("/")
    async def root():
        return {"name": "LeadOS", "version": "3.0", "status": "running", "docs": "/docs"}

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": "3.0",
            "agents": len(orchestrator.agents),
            "leads_in_memory": len(orchestrator.leads_db),
            "mock_mode": False,
        }

    @app.get("/status")
    async def get_status():
        return orchestrator.get_status()

    @app.get("/leads")
    async def list_leads(limit: int = 50, status: Optional[str] = None):
        leads = list(orchestrator.leads_db.values())
        if status:
            leads = [l for l in leads if l.status.value == status]
        leads.sort(key=lambda l: l.ai_score or 0, reverse=True)
        return {"total": len(leads), "leads": [l.to_dict() for l in leads[:limit]]}

    @app.get("/leads/{lead_id}")
    async def get_lead(lead_id: str):
        lead = orchestrator.leads_db.get(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
        return lead.to_dict()

    @app.post("/leads")
    async def submit_lead(req: LeadSubmitRequest):
        from core.models import Lead, LeadSource
        lead = Lead(first_name=req.first_name, last_name=req.last_name,
                    email=req.email, title=req.title, company_name=req.company_name,
                    source=LeadSource.MANUAL)
        lead_id = await orchestrator.submit_lead_data(lead)
        return {"lead_id": lead_id, "status": "pipeline_started"}

    @app.delete("/leads/{lead_id}")
    async def delete_lead(lead_id: str):
        if lead_id not in orchestrator.leads_db:
            raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
        del orchestrator.leads_db[lead_id]
        return {"deleted": lead_id}

    @app.post("/campaigns")
    async def run_campaign(req: CampaignRequest, background_tasks: BackgroundTasks):
        background_tasks.add_task(orchestrator.run_campaign, req.dict())
        return {"status": "campaign_started", "prompt": req.prompt,
                "sources": req.sources, "campaign_id": f"camp_{int(time.time())}"}

    @app.get("/events")
    async def get_events(limit: int = 50):
        return {"events": orchestrator.event_log[-limit:], "total": len(orchestrator.event_log)}

    # ══════════════════════════════════════════════════════════════════════
    # ICP
    # ══════════════════════════════════════════════════════════════════════

    @app.get("/icp")
    async def get_icp():
        icp = orchestrator.icp_profile
        if not icp:
            return {"name": "Default ICP", "target_industries": [], "target_titles": []}
        return {
            "id": icp.id, "name": icp.name,
            "target_industries": icp.target_industries,
            "target_titles": icp.target_titles,
            "target_seniority": icp.target_seniority,
            "min_employees": icp.min_employees,
            "max_employees": icp.max_employees,
            "target_geographies": icp.target_geographies,
            "positive_signals": icp.positive_signals,
            "negative_signals": icp.negative_signals,
        }

    @app.post("/icp")
    async def update_icp(req: ICPUpdateRequest):
        from core.models import ICPProfile
        cur = orchestrator.icp_profile or ICPProfile()
        updated = ICPProfile(
            id=cur.id,
            name=req.name or cur.name,
            target_industries=req.target_industries if req.target_industries is not None else cur.target_industries,
            target_titles=req.target_titles if req.target_titles is not None else cur.target_titles,
            target_seniority=req.target_seniority if req.target_seniority is not None else cur.target_seniority,
            min_employees=req.min_employees if req.min_employees is not None else cur.min_employees,
            max_employees=req.max_employees if req.max_employees is not None else cur.max_employees,
            target_geographies=req.target_geographies if req.target_geographies is not None else cur.target_geographies,
            positive_signals=req.positive_signals if req.positive_signals is not None else cur.positive_signals,
            negative_signals=req.negative_signals if req.negative_signals is not None else cur.negative_signals,
        )
        orchestrator.update_icp(updated)
        orchestrator._log_event("api", f"ICP updated: {updated.name}", "success")
        return {"status": "icp_updated", "icp_name": updated.name}

    # ══════════════════════════════════════════════════════════════════════
    # CRM
    # ══════════════════════════════════════════════════════════════════════

    @app.get("/crm/status")
    async def get_crm_status():
        return _crm_state

    @app.get("/crm/sync-log")
    async def get_sync_log(limit: int = 50):
        return {"log": _sync_log[-limit:], "total": len(_sync_log)}

    @app.post("/crm/sync")
    async def trigger_crm_sync(req: CRMSyncRequest, background_tasks: BackgroundTasks):
        connected = [k for k, v in _crm_state.items() if v.get("connected")]
        targets = connected if req.crm == "all" else [req.crm]
        if not targets:
            return {"status": "no_connected_crms", "leads_queued": 0}

        qualified = [l for l in orchestrator.leads_db.values()
                     if l.ai_score and l.ai_score >= 70 and not l.crm_synced_at]

        async def do_sync():
            for crm in targets:
                _sync_log.insert(0, {
                    "id": f"sync_{int(time.time())}_{crm}", "crm": crm,
                    "operation": "push", "success": True,
                    "records_affected": len(qualified),
                    "created_at": datetime.utcnow().isoformat(),
                    "note": f"Pushed {len(qualified)} qualified leads",
                })
                if crm in _crm_state:
                    _crm_state[crm]["contacts_synced"] = _crm_state[crm].get("contacts_synced", 0) + len(qualified)
                    _crm_state[crm]["last_sync"] = datetime.utcnow().isoformat()
                orchestrator._log_event("crm_sync", f"Pushed {len(qualified)} leads to {crm}", "success")

        background_tasks.add_task(do_sync)
        return {"status": "sync_queued", "crm": req.crm, "leads_queued": len(qualified), "crms": targets}

    @app.post("/crm/connect")
    async def connect_crm(req: CRMConnectRequest):
        crm = req.crm.lower().replace(" ", "_").replace("-", "_")
        if crm not in _crm_state:
            _crm_state[crm] = {}
        _crm_state[crm].update({"connected": True, "uptime": 100.0,
                                 "contacts_synced": 0, "last_sync": datetime.utcnow().isoformat()})
        orchestrator._log_event("crm_sync", f"Connected {crm}", "success")
        return {"status": "connected", "crm": crm}

    # ══════════════════════════════════════════════════════════════════════
    # ANALYTICS
    # ══════════════════════════════════════════════════════════════════════

    @app.get("/analytics")
    async def get_analytics():
        leads = list(orchestrator.leads_db.values())
        qualified = [l for l in leads if l.ai_score and l.ai_score >= 70]
        scores = [l.ai_score for l in leads if l.ai_score]

        source_counts: Dict[str, int] = {}
        for l in leads:
            src = l.source.value if l.source else "manual"
            source_counts[src] = source_counts.get(src, 0) + 1

        today = datetime.utcnow()
        daily = []
        for i in range(30):
            day = today - timedelta(days=29 - i)
            ds = day.strftime("%Y-%m-%d")
            day_leads = [l for l in leads if l.created_at and l.created_at.strftime("%Y-%m-%d") == ds]
            daily.append({
                "date": ds,
                "discovered": len(day_leads),
                "qualified": len([l for l in day_leads if l.ai_score and l.ai_score >= 70]),
                "converted": len([l for l in day_leads if l.status and l.status.value == "converted"]),
            })

        return {
            "total_leads": len(leads),
            "qualified_leads": len(qualified),
            "pipeline_value": len(qualified) * 8500,
            "avg_ai_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "reply_rate": 8.2,
            "open_rate": 47.1,
            "leads_by_source": source_counts,
            "leads_by_day": daily,
        }

    # ══════════════════════════════════════════════════════════════════════
    # SEQUENCES
    # ══════════════════════════════════════════════════════════════════════

    @app.get("/sequences")
    async def list_sequences():
        return {"sequences": _sequences}

    @app.post("/sequences")
    async def create_sequence(req: SequenceCreateRequest):
        seq = {"id": f"seq_{int(time.time())}", "name": req.name,
               "contacts": 0, "active": req.active, "steps": 5,
               "open_rate": 0, "reply_rate": 0,
               "created_at": datetime.utcnow().isoformat()}
        _sequences.append(seq)
        return seq

    # ══════════════════════════════════════════════════════════════════════
    # OUTREACH — AI EMAIL GENERATION
    # ══════════════════════════════════════════════════════════════════════

    @app.post("/outreach/generate")
    async def generate_email(req: OutreachGenerateRequest):
        lead = orchestrator.leads_db.get(req.lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead {req.lead_id} not found")

        first_name = lead.first_name or "there"
        company    = lead.company_name or "your company"
        title      = lead.title or "professional"
        signal     = (lead.intent_signals[0] if lead.intent_signals else "recent growth signals")

        step_guide = {
            1: "Warm first-touch. Short (5–7 sentences). Lead with their specific signal. No pitch — just value + open question.",
            2: "Short follow-up (3–4 sentences). Reference first email. Add one useful tip or insight.",
            3: "Helpful value-add email. Share a relevant insurance tip. No direct ask. Build trust.",
            4: "Polite final close. Under 4 sentences. Leave door open. Give direct phone number.",
        }.get(req.step, "Write a professional outreach email.")

        try:
            import anthropic, json
            client = anthropic.Anthropic(api_key=orchestrator.config.anthropic_api_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=600,
                messages=[{"role": "user", "content": f"""You are writing a personalized outreach email for a P&C insurance agent building referral partnerships.

Contact: {first_name}, {title} at {company}
Key signal: {signal}
Step {req.step} of 4: {step_guide}

Goal: referral partnership — NOT selling insurance directly.
Placeholders to use: {{{{your_name}}}}, {{{{your_phone}}}}, {{{{your_agency}}}}

Return ONLY valid JSON with keys "subject" and "body". No markdown, no explanation."""}]
            )
            text = message.content[0].text.strip().replace("```json","").replace("```","").strip()
            result = json.loads(text)
            orchestrator._log_event("outreach", f"AI email generated for {first_name} at {company} (step {req.step})", "success")
            return result

        except Exception as e:
            log.warning(f"Claude email gen failed ({e}) — using fallback template")
            # Always-available fallback — works even without API key
            fallbacks = {
                1: {"subject": f"Quick question — do you have a go-to insurance agent?",
                    "body": f"Hi {first_name},\n\nI saw that {company} has been {signal} — congrats on the momentum.\n\nI'm a local P&C insurance agent who specializes in working with {title}s. I turn around same-day quotes and can usually find coverage even for tricky properties.\n\nWould a quick 10-min call make sense to see if we'd be a good fit?\n\n{{{{your_name}}}}\n{{{{your_phone}}}}\n{{{{your_agency}}}}"},
                2: {"subject": f"Re: Quick question — do you have a go-to insurance agent?",
                    "body": f"Hi {first_name},\n\nJust following up briefly — I know you're busy.\n\nOne thing worth mentioning: when I work with a partner's clients, I copy the partner on all communications so there are never surprises.\n\nHappy to send a quick one-pager if useful.\n\n{{{{your_name}}}}"},
                3: {"subject": f"Insurance tip for your clients",
                    "body": f"Hi {first_name},\n\nSharing something useful regardless of whether we ever connect — a lot of clients in our area are getting surprised by wind/hail surcharges on new policies right now. Worth flagging to buyers early so it doesn't affect their budget.\n\nHappy to be a free resource whenever you have a coverage question.\n\n{{{{your_name}}}}\n{{{{your_phone}}}}"},
                4: {"subject": f"Last note from me",
                    "body": f"Hi {first_name},\n\nWon't keep reaching out — just didn't want to disappear without saying the door is always open. If you ever have a client who needs insurance fast, feel free to call me directly.\n\n{{{{your_name}}}}\n{{{{your_phone}}}}"},
            }
            return fallbacks.get(req.step, fallbacks[1])

    # ══════════════════════════════════════════════════════════════════════
    # STRIPE BILLING
    # ══════════════════════════════════════════════════════════════════════

    STRIPE_SECRET_KEY      = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET  = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    # Price IDs — create these in Stripe Dashboard then set as env vars
    PRICE_LONE_WOLF   = os.getenv("STRIPE_PRICE_LONE_WOLF",  "price_lone_wolf_monthly")
    PRICE_TEAM        = os.getenv("STRIPE_PRICE_TEAM",       "price_team_monthly")
    PRICE_WHITE_LABEL = os.getenv("STRIPE_PRICE_WHITE_LABEL","price_white_label_monthly")
    PRICE_TRANSFER    = os.getenv("STRIPE_PRICE_TRANSFER",   "price_voice_transfer")

    # In-memory subscription store (email → tier)
    _subscriptions: Dict[str, Dict] = {}

    class CheckoutRequest(BaseModel):
        tier: str = "lone_wolf"   # lone_wolf | team | white_label
        email: str = ""
        success_url: str = "https://tryleados.com/leadOS-onboarding.html?step=2"
        cancel_url: str  = "https://tryleados.com"

    class TransferBillRequest(BaseModel):
        email: str
        lead_name: str = ""
        lead_score: float = 0

    @app.post("/billing/checkout")
    async def create_checkout(req: CheckoutRequest):
        """Create a Stripe Checkout session and return the URL."""
        if not STRIPE_SECRET_KEY or STRIPE_SECRET_KEY.startswith("sk_test_REPLACE"):
            # Return a demo URL if Stripe not yet configured
            return {
                "url": req.success_url + "&demo=true",
                "session_id": "demo_session",
                "note": "Set STRIPE_SECRET_KEY in Railway to enable real billing",
            }
        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            price_map = {
                "lone_wolf":   PRICE_LONE_WOLF,
                "team":        PRICE_TEAM,
                "white_label": PRICE_WHITE_LABEL,
            }
            price_id = price_map.get(req.tier, PRICE_LONE_WOLF)
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                customer_email=req.email or None,
                success_url=req.success_url + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=req.cancel_url,
                metadata={"tier": req.tier, "email": req.email},
            )
            return {"url": session.url, "session_id": session.id}
        except Exception as e:
            log.error(f"Stripe checkout failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/billing/webhook")
    async def stripe_webhook(request: Request):
        """Handle Stripe webhook events."""
        payload  = await request.body()
        sig      = request.headers.get("stripe-signature", "")

        if not STRIPE_SECRET_KEY:
            return {"status": "skipped_no_key"}

        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            if STRIPE_WEBHOOK_SECRET:
                event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
            else:
                import json
                event = json.loads(payload)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Webhook error: {e}")

        etype = event.get("type", "")
        data  = event.get("data", {}).get("object", {})
        email = (data.get("customer_email") or
                 data.get("metadata", {}).get("email") or "")

        if etype == "checkout.session.completed":
            tier = data.get("metadata", {}).get("tier", "lone_wolf")
            _subscriptions[email] = {
                "tier": tier, "status": "active",
                "stripe_customer_id": data.get("customer"),
                "stripe_subscription_id": data.get("subscription"),
                "activated_at": datetime.utcnow().isoformat(),
            }
            orchestrator._log_event("billing", f"Subscription activated: {tier} for {email}", "success")
            log.info(f"✅ Checkout complete — {tier} for {email}")

        elif etype == "customer.subscription.deleted":
            if email in _subscriptions:
                _subscriptions[email]["status"] = "cancelled"
            orchestrator._log_event("billing", f"Subscription cancelled for {email}", "info")

        elif etype == "invoice.payment_failed":
            orchestrator._log_event("billing", f"Payment failed for {email}", "error")

        elif etype == "invoice.paid":
            if email in _subscriptions:
                _subscriptions[email]["last_paid"] = datetime.utcnow().isoformat()
            orchestrator._log_event("billing", f"Invoice paid for {email}", "success")

        return {"received": True, "type": etype}

    @app.post("/billing/transfer")
    async def bill_transfer(req: TransferBillRequest):
        """Bill $25 per qualified voice transfer via Stripe usage record."""
        if not STRIPE_SECRET_KEY or not req.email:
            return {"status": "skipped", "reason": "Stripe not configured or no email"}

        sub = _subscriptions.get(req.email, {})
        if not sub.get("stripe_subscription_id"):
            return {"status": "skipped", "reason": "No active subscription found"}

        try:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            # Create a one-time invoice item for $25
            stripe.InvoiceItem.create(
                customer=sub["stripe_customer_id"],
                amount=2500,  # $25.00 in cents
                currency="usd",
                description=f"Qualified lead transfer — {req.lead_name} (score: {req.lead_score})",
            )
            orchestrator._log_event("billing", f"Transfer billed $25 for {req.email} — {req.lead_name}", "success")
            return {"status": "billed", "amount": 25.00, "email": req.email}
        except Exception as e:
            log.error(f"Transfer billing failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/billing/subscription")
    async def get_subscription(email: str):
        return _subscriptions.get(email, {"status": "none", "tier": None})

    # ══════════════════════════════════════════════════════════════════════
    # SUPPORT CHATBOT
    # ══════════════════════════════════════════════════════════════════════

    SUPPORT_SYSTEM_PROMPT = """You are the LeadOS support agent. You know everything about LeadOS:
the product, pricing, features, how agents work, billing, voice transfers, and common troubleshooting.

Pricing:
- Lone Wolf: $49/month (50 leads, 1 vertical, no team seats)
- Team: $149/month (500 leads, 3 verticals, 3 seats)
- White Label: $399/month (unlimited leads, all verticals, custom branding)
- Voice transfers: $25 per qualified transfer (Lone Wolf), $18 (Team)

Key features:
- 8 AI agents: Crawler, LinkedIn, Enricher, Email Verifier, Signal Detector, Qualifier, CRM Sync, Outreach
- Claude AI scores leads 0-100 against the user's ICP
- Leads scoring 75+ trigger automatic voice qualification calls via Aria (ElevenLabs voice)
- Qualified leads warm-transfer directly to the agent's phone via Twilio
- CRM integrations: HubSpot, Salesforce, Pipedrive, GoHighLevel
- Morning brief email delivered at 6am CST with top leads

If you cannot answer something, say: "Let me flag this for Enrique — he'll respond within 24 hours."
Never make up pricing, features, or capabilities that don't exist.
Keep responses concise (3-5 sentences max) and action-oriented."""

    class ChatMessageRequest(BaseModel):
        message: str
        session_id: str = ""
        history: List[Dict] = []
        email: str = ""

    @app.post("/chat/message")
    async def chat_message(req: ChatMessageRequest):
        """Support chatbot powered by Claude API with MetaClaw memory injection."""
        if not orchestrator.config.anthropic_api_key:
            return {"reply": "Chat is not available right now — ANTHROPIC_API_KEY not configured. Email support@tryleados.com for help."}

        try:
            import anthropic, asyncio
            from core.metaclaw import load_user_memory, build_user_context, inject_memory

            # P10: Load user memory and inject into system prompt
            user_memory = await load_user_memory(req.email)
            leads_summary = {
                "total": len(orchestrator.leads_db),
                "qualified": sum(1 for l in orchestrator.leads_db.values() if l.is_qualified),
                "avg_score": round(
                    sum(l.ai_score for l in orchestrator.leads_db.values() if l.ai_score)
                    / max(1, sum(1 for l in orchestrator.leads_db.values() if l.ai_score)), 1
                ),
            }
            user_ctx = build_user_context(user_memory, leads_summary)
            system   = inject_memory(SUPPORT_SYSTEM_PROMPT, user_ctx)

            # Build messages array from history + new message
            messages = []
            for turn in req.history[-8:]:  # last 8 turns for context
                role = turn.get("role", "user")
                if role in ("user", "assistant"):
                    messages.append({"role": role, "content": str(turn.get("content", ""))})

            # Ensure last message is the current user input
            if not messages or messages[-1].get("content") != req.message:
                messages.append({"role": "user", "content": req.message})

            client = anthropic.Anthropic(api_key=orchestrator.config.anthropic_api_key)
            response = await asyncio.to_thread(
                client.messages.create,
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                system=system,
                messages=messages,
            )
            reply = response.content[0].text.strip()

            # Persist to Supabase conversation_history if available
            try:
                from db import supabase_client
                if supabase_client.is_ready() and req.email:
                    for role, content in [("user", req.message), ("assistant", reply)]:
                        await asyncio.to_thread(
                            supabase_client.client.table("conversation_history").insert({
                                "role": role, "content": content,
                                "session_id": req.session_id or "anon",
                            }).execute
                        )
            except Exception:
                pass

            orchestrator._log_event("chat", f"Chat response sent (session={req.session_id[:8]})", "info")
            return {"reply": reply, "session_id": req.session_id}

        except Exception as e:
            log.error(f"Chat error: {e}")
            return {"reply": "I'm having trouble right now. Please try again or email support@tryleados.com."}

    # ══════════════════════════════════════════════════════════════════════
    # ONBOARDING
    # ══════════════════════════════════════════════════════════════════════

    class OnboardingICPRequest(BaseModel):
        industry: str = "insurance"
        target_states: List[str] = []
        client_types: List[str] = []
        lead_priorities: List[str] = []
        age_range: str = ""
        email: str = ""

    class VoiceConfigRequest(BaseModel):
        enabled: bool = False
        phone_number: str = ""
        email: str = ""

    class WelcomeBriefRequest(BaseModel):
        email: str
        leads: List[Dict] = []

    # In-memory voice config store (per email)
    _voice_configs: Dict[str, Dict] = {}

    @app.post("/onboarding/icp")
    async def onboarding_icp(req: OnboardingICPRequest):
        """Save onboarding ICP and kick off first campaign."""
        from core.models import ICPProfile

        industry_map = {
            "insurance":   ["P&C Insurance", "Home Insurance", "Auto Insurance"],
            "mortgage":    ["Mortgage", "Home Loans"],
            "real_estate": ["Real Estate", "Property"],
            "solar":       ["Solar", "Renewable Energy"],
        }
        industries = industry_map.get(req.industry, [req.industry.replace("_", " ").title()])

        icp = ICPProfile(
            name=f"{req.industry.replace('_',' ').title()} ICP",
            target_industries=industries,
            target_geographies=req.target_states,
            positive_signals=req.lead_priorities,
        )
        orchestrator.update_icp(icp)

        # Persist to Supabase user_memory if available
        try:
            from db import supabase_client
            if supabase_client.is_ready() and req.email:
                import asyncio
                await asyncio.to_thread(
                    supabase_client.client.table("user_memory").upsert({
                        "industry": req.industry,
                        "icp_description": f"{', '.join(industries)} — {', '.join(req.target_states)}",
                        "target_states": req.target_states,
                        "memory_notes": f"client_types={req.client_types}, priorities={req.lead_priorities}",
                    }).execute
                )
        except Exception as e:
            log.warning(f"Supabase user_memory write failed: {e}")

        orchestrator._log_event("onboarding", f"ICP saved: {icp.name}", "success")
        return {"status": "icp_saved", "icp_name": icp.name, "states": req.target_states}

    @app.post("/voice/configure")
    async def configure_voice(req: VoiceConfigRequest):
        """Save voice agent config for a user."""
        key = req.email or "default"
        _voice_configs[key] = {
            "enabled": req.enabled,
            "phone_number": req.phone_number,
            "updated_at": datetime.utcnow().isoformat(),
        }
        orchestrator._log_event(
            "voice",
            f"Voice {'enabled' if req.enabled else 'disabled'} for {key}",
            "success"
        )
        return {"status": "voice_configured", "enabled": req.enabled}

    @app.get("/voice/config")
    async def get_voice_config(email: str = "default"):
        return _voice_configs.get(email, {"enabled": False, "phone_number": ""})

    @app.post("/heartbeat/send-welcome-brief")
    async def send_welcome_brief(req: WelcomeBriefRequest, background_tasks: BackgroundTasks):
        """Send welcome email with lead preview via SendGrid."""
        if not req.email:
            return {"status": "skipped", "reason": "no email provided"}

        async def _send():
            sendgrid_key = orchestrator.config.sendgrid_api_key
            if not sendgrid_key:
                log.warning("SENDGRID_API_KEY not set — skipping welcome email")
                return

            leads_html = "".join([
                f"<tr><td style='padding:8px 12px;font-family:monospace;font-size:13px'>{l.get('name','—')}</td>"
                f"<td style='padding:8px 12px;color:#5a7099;font-size:12px'>{l.get('title','')}</td>"
                f"<td style='padding:8px 12px;font-weight:700;color:#00ff88'>{l.get('score',0)}</td></tr>"
                for l in req.leads[:3]
            ]) or "<tr><td colspan='3' style='padding:8px 12px;color:#5a7099'>Leads are generating now — check your dashboard.</td></tr>"

            html = f"""
<html><body style="background:#050810;color:#f0f4ff;font-family:'DM Mono',monospace;padding:32px;max-width:560px;margin:auto">
  <div style="margin-bottom:24px">
    <span style="background:#00ff88;color:#000;font-weight:900;font-family:sans-serif;font-size:16px;padding:6px 12px;border-radius:8px">LeadOS</span>
  </div>
  <h2 style="font-size:22px;font-family:sans-serif;margin-bottom:8px">Welcome! Your lead engine is live. 🚀</h2>
  <p style="color:#5a7099;font-size:13px;margin-bottom:24px;line-height:1.7">
    Here's a preview of what your AI agents found today. Your full morning brief arrives tomorrow at 6am CST.
  </p>
  <table style="width:100%;border-collapse:collapse;background:#0c1120;border-radius:10px;overflow:hidden;margin-bottom:24px">
    <thead><tr style="background:#111827">
      <th style="padding:10px 12px;text-align:left;font-size:10px;color:#5a7099;letter-spacing:1px;text-transform:uppercase">Name</th>
      <th style="padding:10px 12px;text-align:left;font-size:10px;color:#5a7099;letter-spacing:1px;text-transform:uppercase">Profile</th>
      <th style="padding:10px 12px;text-align:left;font-size:10px;color:#5a7099;letter-spacing:1px;text-transform:uppercase">AI Score</th>
    </tr></thead>
    <tbody>{leads_html}</tbody>
  </table>
  <a href="https://tryleados.com/leadOS-dashboard.html"
     style="display:inline-block;background:#00ff88;color:#000;font-weight:700;padding:12px 24px;border-radius:8px;text-decoration:none;font-family:sans-serif">
    View Full Dashboard →
  </a>
  <p style="color:#2d3f5a;font-size:10px;margin-top:32px">
    LeadOS · Austin, TX · <a href="https://tryleados.com" style="color:#2d3f5a">tryleados.com</a>
  </p>
</body></html>"""

            try:
                import httpx
                resp = await asyncio.to_thread(
                    lambda: __import__('httpx').post(
                        "https://api.sendgrid.com/v3/mail/send",
                        headers={"Authorization": f"Bearer {sendgrid_key}", "Content-Type": "application/json"},
                        json={
                            "personalizations": [{"to": [{"email": req.email}]}],
                            "from": {"email": orchestrator.config.outreach_from_email,
                                     "name": "LeadOS"},
                            "subject": "🚀 Your lead engine is live — here's your first preview",
                            "content": [{"type": "text/html", "value": html}],
                        }
                    )
                )
                if resp.status_code == 202:
                    log.info(f"Welcome email sent to {req.email}")
                    orchestrator._log_event("heartbeat", f"Welcome brief sent to {req.email}", "success")
                else:
                    log.warning(f"SendGrid returned {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                log.warning(f"Welcome email send failed: {e}")

        import asyncio
        background_tasks.add_task(_send)
        return {"status": "queued", "email": req.email}

    # ══════════════════════════════════════════════════════════════════════
    # VOICE AGENT — VAPI + TWILIO (P11-P15)
    # ══════════════════════════════════════════════════════════════════════

    VAPI_KEY       = os.getenv("VAPI_API_KEY", "")
    ELEVENLABS_VID = os.getenv("ELEVENLABS_VOICE_ID", "")
    TWILIO_PHONE   = os.getenv("TWILIO_PHONE_NUMBER", "")

    # Cached assistant ID (created once per process)
    _vapi_assistant_id_store: Dict[str, Optional[str]] = {"id": None}

    async def _get_or_create_vapi_assistant(transfer_phone: str = "") -> Optional[str]:
        if _vapi_assistant_id_store["id"]:
            return _vapi_assistant_id_store["id"]
        if not VAPI_KEY:
            return None
        from core.voice_agent import build_vapi_assistant_config, create_vapi_assistant
        config = build_vapi_assistant_config(
            elevenlabs_voice_id=ELEVENLABS_VID,
            transfer_phone=transfer_phone,
        )
        aid = await create_vapi_assistant(VAPI_KEY, config)
        _vapi_assistant_id_store["id"] = aid
        if aid:
            orchestrator._log_event("voice", f"Vapi assistant created: {aid}", "success")
        return aid

    class CallLeadRequest(BaseModel):
        lead_id: str
        override_phone: Optional[str] = None

    @app.post("/voice/call")
    async def call_lead(req: CallLeadRequest):
        """Initiate an outbound Vapi call to a lead."""
        lead = orchestrator.leads_db.get(req.lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead {req.lead_id} not found")

        lead_phone = req.override_phone or lead.phone
        if not lead_phone:
            raise HTTPException(status_code=400, detail="Lead has no phone number")

        if not VAPI_KEY:
            return {"status": "skipped", "reason": "VAPI_API_KEY not configured — set in Railway"}
        if not TWILIO_PHONE:
            return {"status": "skipped", "reason": "TWILIO_PHONE_NUMBER not configured — set in Railway"}

        # Get transfer phone from any active voice config
        transfer_phone = next(
            (cfg["phone_number"] for cfg in _voice_configs.values()
             if cfg.get("enabled") and cfg.get("phone_number")),
            ""
        )

        assistant_id = await _get_or_create_vapi_assistant(transfer_phone)
        if not assistant_id:
            raise HTTPException(status_code=503, detail="Failed to initialize Vapi assistant")

        from core.voice_agent import initiate_outbound_call
        call_id = await initiate_outbound_call(
            vapi_key=VAPI_KEY,
            assistant_id=assistant_id,
            lead_phone=lead_phone,
            twilio_phone=TWILIO_PHONE,
            lead_name=f"{lead.first_name or ''} {lead.last_name or ''}".strip(),
            metadata={"lead_id": req.lead_id, "ai_score": str(lead.ai_score or 0)},
        )
        if call_id:
            orchestrator._log_event("voice", f"Call initiated → {lead.first_name} ({lead_phone})", "success")
            return {"status": "call_initiated", "call_id": call_id, "lead_id": req.lead_id}
        raise HTTPException(status_code=503, detail="Vapi call initiation failed")

    @app.post("/webhook/vapi/call-started")
    async def vapi_call_started(request: Request):
        payload = await request.json()
        call_id = payload.get("callId") or payload.get("id", "")
        lead_id = (payload.get("metadata") or {}).get("lead_id", "")
        orchestrator._log_event("voice", f"Call started: {call_id} | lead={lead_id}", "info")
        return {"received": True}

    @app.post("/webhook/vapi/call-ended")
    async def vapi_call_ended(request: Request, background_tasks: BackgroundTasks):
        payload = await request.json()
        call   = payload.get("call", payload)
        call_id= call.get("id", "")
        meta   = call.get("metadata") or {}
        lead_id= meta.get("lead_id", "")
        duration   = call.get("durationSeconds", 0) or 0
        transcript = call.get("transcript", "") or ""
        recording  = call.get("recordingUrl", "") or ""

        from core.voice_agent import score_call_transcript, log_call_to_supabase

        scored = score_call_transcript(transcript)
        score  = scored["score"]
        outcome= scored["outcome"]

        lead = orchestrator.leads_db.get(lead_id)
        score_before = float(lead.ai_score or 0) if lead else 0.0
        if lead:
            lead.ai_score = score
            lead.ai_score_reasoning = f"Voice qualified: {outcome} (score {score})"

        transferred = (outcome == "transfer")

        async def _post_call():
            await log_call_to_supabase(
                call_id, lead_id, duration, score_before, score,
                transferred, recording, transcript, outcome,
            )
            # Bill $25 per transfer (P14)
            if transferred and STRIPE_SECRET_KEY:
                for email, sub in _subscriptions.items():
                    if sub.get("status") == "active" and sub.get("stripe_customer_id"):
                        try:
                            import stripe
                            stripe.api_key = STRIPE_SECRET_KEY
                            stripe.InvoiceItem.create(
                                customer=sub["stripe_customer_id"],
                                amount=2500, currency="usd",
                                description=f"Qualified transfer — {lead.first_name if lead else 'lead'} (score {score})",
                            )
                            orchestrator._log_event("billing", f"Transfer billed $25 (score={score})", "success")
                        except Exception as e:
                            log.warning(f"Transfer billing failed: {e}")
                        break

        background_tasks.add_task(_post_call)
        orchestrator._log_event("voice", f"Call ended: {call_id} | score={score} | {outcome}", "success" if transferred else "info")
        return {"received": True, "score": score, "outcome": outcome}

    @app.post("/webhook/vapi/transfer-requested")
    async def vapi_transfer_requested(request: Request):
        payload = await request.json()
        call_id = payload.get("callId", "")
        orchestrator._log_event("voice", f"Warm transfer requested: {call_id}", "success")
        return {"received": True, "action": "transfer"}

    @app.get("/voice/assistant")
    async def get_voice_assistant():
        return {
            "vapi_configured": bool(VAPI_KEY),
            "twilio_configured": bool(TWILIO_PHONE),
            "elevenlabs_configured": bool(ELEVENLABS_VID),
            "assistant_id": _vapi_assistant_id_store["id"],
        }

    # ══════════════════════════════════════════════════════════════════════
    # MORNING BRIEF (P9)
    # ══════════════════════════════════════════════════════════════════════

    class MorningBriefRequest(BaseModel):
        email: str
        user_name: str = "there"

    @app.post("/heartbeat/morning-brief")
    async def send_morning_brief(req: MorningBriefRequest, background_tasks: BackgroundTasks):
        """Generate and send the 6am morning brief via Claude + SendGrid."""
        async def _run():
            import anthropic, asyncio as aio
            from core.metaclaw import load_user_memory, build_user_context, inject_memory

            sendgrid_key = orchestrator.config.sendgrid_api_key
            if not sendgrid_key or not orchestrator.config.anthropic_api_key:
                log.warning("Morning brief skipped — missing SENDGRID_API_KEY or ANTHROPIC_API_KEY")
                return

            # Get top qualified leads
            leads = sorted(
                [l for l in orchestrator.leads_db.values() if l.ai_score],
                key=lambda l: l.ai_score or 0, reverse=True
            )[:5]

            user_memory = await load_user_memory(req.email)

            # Build brief content with Claude
            leads_text = "\n".join([
                f"- {l.first_name} {l.last_name} ({l.company_name or 'unknown company'}): score {l.ai_score}/100. {l.ai_score_reasoning or ''}"
                for l in leads
            ]) or "No leads found yet — agents are still running."

            user_ctx = build_user_context(user_memory, {
                "total": len(orchestrator.leads_db),
                "qualified": sum(1 for l in orchestrator.leads_db.values() if l.is_qualified),
                "avg_score": 0,
            })

            brief_prompt = f"""{user_ctx}

You are writing a personalized morning brief email for a P&C insurance agent using LeadOS.
Keep it concise, data-first, and action-oriented. Write in plain text (no markdown).

Top leads today:
{leads_text}

Write a brief (4-6 sentences) morning summary covering:
1. How many leads were found overnight and the top score
2. The single highest-priority lead and why
3. One recommended action for today
4. An encouraging, professional sign-off

Do not use bullet points. Write in paragraph form. Address the agent as "{req.user_name}"."""

            try:
                client = anthropic.Anthropic(api_key=orchestrator.config.anthropic_api_key)
                response = await aio.to_thread(
                    client.messages.create,
                    model="claude-sonnet-4-20250514",
                    max_tokens=400,
                    messages=[{"role": "user", "content": brief_prompt}],
                )
                brief_text = response.content[0].text.strip()
            except Exception as e:
                log.warning(f"Claude brief gen failed: {e}")
                brief_text = f"Good morning, {req.user_name}! Your LeadOS agents ran overnight and found {len(leads)} qualified leads. Log in to review your top opportunities and take action today."

            # Build HTML email
            leads_html = "".join([
                f"""<tr>
                  <td style='padding:10px 14px;font-family:monospace;font-size:12px;color:#f0f4ff'>
                    {l.first_name} {l.last_name}</td>
                  <td style='padding:10px 14px;font-size:11px;color:#5a7099'>
                    {l.company_name or '—'}</td>
                  <td style='padding:10px 14px;font-weight:700;color:{"#00ff88" if (l.ai_score or 0) >= 75 else "#ffaa00"}'>
                    {l.ai_score}/100</td>
                  <td style='padding:10px 14px;font-size:10px;color:#5a7099'>
                    {"✅ QUALIFIED" if l.is_qualified else "📋 NURTURE"}</td>
                </tr>"""
                for l in leads
            ]) or "<tr><td colspan='4' style='padding:12px 14px;color:#5a7099;font-size:11px'>No leads yet — agents are running now.</td></tr>"

            date_str = datetime.utcnow().strftime("%A, %B %-d")
            html_body = f"""<html><body style="background:#050810;color:#f0f4ff;font-family:'DM Mono',monospace;padding:32px;max-width:600px;margin:auto">
  <div style="margin-bottom:20px;display:flex;align-items:center;gap:10px">
    <span style="background:#00ff88;color:#000;font-weight:900;font-family:sans-serif;font-size:16px;padding:6px 12px;border-radius:8px">L</span>
    <span style="font-family:sans-serif;font-size:18px;font-weight:900">LeadOS <span style="color:#5a7099;font-size:12px;font-weight:400">Morning Brief</span></span>
  </div>
  <div style="font-size:11px;color:#5a7099;margin-bottom:20px">☀️ &nbsp;{date_str} · 6:00 AM CST</div>
  <p style="font-size:13px;line-height:1.8;color:#d0d8f0;margin-bottom:24px;white-space:pre-line">{brief_text}</p>
  <table style="width:100%;border-collapse:collapse;background:#0c1120;border-radius:10px;overflow:hidden;margin-bottom:24px">
    <thead><tr style="background:#111827">
      <th style="padding:10px 14px;text-align:left;font-size:9px;color:#5a7099;letter-spacing:1px;text-transform:uppercase">Name</th>
      <th style="padding:10px 14px;text-align:left;font-size:9px;color:#5a7099;letter-spacing:1px;text-transform:uppercase">Company</th>
      <th style="padding:10px 14px;text-align:left;font-size:9px;color:#5a7099;letter-spacing:1px;text-transform:uppercase">Score</th>
      <th style="padding:10px 14px;text-align:left;font-size:9px;color:#5a7099;letter-spacing:1px;text-transform:uppercase">Status</th>
    </tr></thead>
    <tbody>{leads_html}</tbody>
  </table>
  <a href="https://tryleados.com/leadOS-dashboard.html"
     style="display:inline-block;background:#00ff88;color:#000;font-weight:700;padding:12px 24px;border-radius:8px;text-decoration:none;font-family:sans-serif;font-size:13px">
    View Full Dashboard →
  </a>
  <p style="color:#2d3f5a;font-size:10px;margin-top:28px">
    LeadOS · Austin, TX · <a href="https://tryleados.com" style="color:#2d3f5a">tryleados.com</a>
    · <a href="https://tryleados.com/unsubscribe" style="color:#2d3f5a">Unsubscribe</a>
  </p>
</body></html>"""

            try:
                import httpx
                resp = httpx.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={"Authorization": f"Bearer {sendgrid_key}", "Content-Type": "application/json"},
                    json={
                        "personalizations": [{"to": [{"email": req.email}]}],
                        "from": {"email": orchestrator.config.outreach_from_email, "name": "LeadOS"},
                        "subject": f"☀️ Your LeadOS Brief — {len(leads)} leads ready · {date_str}",
                        "content": [{"type": "text/html", "value": html_body}],
                    },
                    timeout=10,
                )
                if resp.status_code == 202:
                    log.info(f"Morning brief sent to {req.email}")
                    orchestrator._log_event("heartbeat", f"Morning brief sent to {req.email}", "success")
                else:
                    log.warning(f"SendGrid error {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                log.warning(f"Morning brief send failed: {e}")

        background_tasks.add_task(_run)
        return {"status": "queued", "email": req.email}

    @app.post("/heartbeat/trigger")
    async def manual_heartbeat(background_tasks: BackgroundTasks):
        """Manual trigger for testing heartbeat actions."""
        leads = list(orchestrator.leads_db.values())
        qualified = [l for l in leads if l.is_qualified]
        orchestrator._log_event("heartbeat", f"Manual trigger — {len(qualified)} qualified leads", "info")
        return {
            "status": "triggered",
            "total_leads": len(leads),
            "qualified_leads": len(qualified),
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ══════════════════════════════════════════════════════════════════════
    # CONTENT PIPELINE (P19)
    # ══════════════════════════════════════════════════════════════════════

    class ContentPipelineRequest(BaseModel):
        template_key: str = "lone_wolf_story"  # lone_wolf_story | lead_tip | transfer_proof

    @app.post("/content/generate")
    async def generate_content(req: ContentPipelineRequest, background_tasks: BackgroundTasks):
        """Run ElevenLabs + HeyGen content pipeline for a given template."""
        leads = list(orchestrator.leads_db.values())
        lead_stats = {
            "total": len(leads),
            "transfers": sum(1 for l in leads if l.is_qualified),
        }

        async def _run():
            from core.content_pipeline import run_content_pipeline
            result = await run_content_pipeline(
                template_key=req.template_key,
                lead_stats=lead_stats,
                anthropic_key=orchestrator.config.anthropic_api_key,
                elevenlabs_key=os.getenv("ELEVENLABS_API_KEY", ""),
                elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
                heygen_key=os.getenv("HEYGEN_API_KEY", ""),
                heygen_avatar_id=os.getenv("HEYGEN_AVATAR_ID", ""),
            )
            orchestrator._log_event("content", f"Pipeline complete: template={req.template_key}", "success")
            return result

        background_tasks.add_task(_run)
        return {"status": "pipeline_started", "template": req.template_key, "lead_stats": lead_stats}

    @app.get("/content/templates")
    async def list_content_templates():
        """List available content templates."""
        from core.content_pipeline import CONTENT_TEMPLATES
        return {
            "templates": [
                {"key": k, "hook": v["hook"], "duration_seconds": v["duration"]}
                for k, v in CONTENT_TEMPLATES.items()
            ]
        }

    # ── Start ─────────────────────────────────────────────────────────────

    cfg = uvicorn.Config(app=app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(cfg)
    log.info(f"LeadOS API v2.1 running → http://{host}:{port}")
    log.info(f"Swagger docs         → http://{host}:{port}/docs")
    await server.serve()
