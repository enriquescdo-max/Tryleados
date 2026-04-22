# LEADOS — MASTER CLAUDE.md
## Single Source of Truth for Claude Code
## Owner: Enrique Saucedo | We Insure / PEAK6
## Deadline: May 29, 2026 — PEAK6 Trials Submission
## Last Updated: April 20, 2026

---

## STOP. READ THIS ENTIRE FILE BEFORE WRITING A SINGLE LINE OF CODE.

You are Claude Code. This is your complete project briefing for LeadOS.
- This is a PEAK6 Trials submission. The founder is a solo builder.
- Every decision must favor **speed + correctness** over elegance.
- When in doubt: ship it working, refactor later.
- Never hardcode API keys. Always use `process.env.KEY_NAME` or `os.environ["KEY_NAME"]`.
- After each module is complete, confirm it works before moving to the next.

---

## 1. WHAT IS LEADOS

LeadOS is an AI-native lead generation OS for P&C insurance agents — and any other industry via white-label. It runs the Apex 7-layer autonomous agent architecture combined with the MEDVi lean operator model.

**One-line pitch:**
"LeadOS is the first AI OS that finds, qualifies, and delivers leads to insurance agents automatically — while you sleep."

**Live URLs:**
- Frontend: https://tryleados.com (Netlify)
- Backend: https://tryleados-production.up.railway.app (Railway)
- Database: Supabase (vvsshirbxfypjvrdmgls.supabase.co)

**Pricing tiers:**
- Lone Wolf: $49/mo
- Team: $149/mo
- White Label: $399/mo

---

## 2. TECH STACK

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite + Tailwind CSS → Netlify |
| Backend | Python FastAPI → Railway |
| Database | Supabase (Postgres + Auth + RLS) |
| AI Brain | Anthropic Claude API (claude-sonnet-4-20250514) |
| Scraping | Apify actors |
| Auth | Google OAuth + Microsoft OAuth |
| Billing | Stripe |
| Scheduler | APScheduler (Railway cron) |
| Voice | Vapi (warm transfer to agent) |
| Email | ElevenLabs content pipeline |

---

## 3. ENVIRONMENT VARIABLES

All already set in Railway and Netlify. Never hardcode these:

```
# Railway (backend)
ANTHROPIC_API_KEY=process.env.ANTHROPIC_API_KEY
APIFY_API_TOKEN=process.env.APIFY_API_TOKEN
SUPABASE_URL=process.env.SUPABASE_URL
SUPABASE_SERVICE_KEY=process.env.SUPABASE_SERVICE_KEY
MOCK_MODE=false                          ← MUST BE FALSE. CHECK THIS FIRST.
STRIPE_SECRET_KEY=process.env.STRIPE_SECRET_KEY
GOOGLE_CLIENT_ID=403990471402-lf7efr5b1bqb4olgk4n02bjubbkjqt5m
MICROSOFT_CLIENT_ID=be03200f-bf3a-42cf-9ea5-6b83a3294a7d

# Netlify (frontend)
REACT_APP_API_URL=process.env.REACT_APP_API_URL  ← Railway backend URL
```

**FIRST THING TO CHECK:** Go to Railway → LeadOS service → Variables → confirm `MOCK_MODE=false`. If it's `true`, nothing real runs.

---

## 4. APEX 7-LAYER ARCHITECTURE STATUS

| Layer | Name | Status |
|-------|------|--------|
| 1 | Brain (Claude API) | ✅ Live |
| 2 | Memory (Supabase) | ✅ Live |
| 3 | Gateway (FastAPI) | ✅ Live |
| 4 | Skills (5 modules) | ✅ Built |
| 5 | Heartbeat Scheduler | 🔧 Build now |
| 6 | PI Agent | 🔧 Build now |
| 7 | Security | 🔧 Next sprint |

**Skills already built:**
1. Reverse Lead Magnet audit generator
2. AI Marketing Team (3 agents)
3. HeyGen/Submagic video pipeline
4. Email deliverability dashboard + 10-day warm-up sequences
5. Direct Response Copy Engine

---

## 5. DESIGN SYSTEM — $10K UI STANDARD

Apply this to ALL frontend work. No exceptions.

### Stack
- GSAP ScrollTrigger — scroll-driven parallax and cinematic reveals
- Framer Motion — layout transitions and page-load glide effects
- Locomotive Scroll — buttery smooth scrolling on marketing pages
- Aceternity UI — Tracing Beam, Lamp Effect, Aurora background
- Magic UI — Bento Grid (varying card sizes), Meteors, Shiny Buttons
- Shadcn/UI — base component layer for all interactive elements
- Liquid Glass — dashersw/liquid-glass-js (WebGL refraction, not CSS blur)
- Three.js — for any 3D or particle effects

### Glass Treatment
```css
backdrop-filter: blur(12px);
border: 1px solid rgba(255,255,255,0.1);  /* rim-light */
transform: translateZ(0);                  /* GPU acceleration */
/* Add subtle top-left specular highlight */
background: linear-gradient(135deg, rgba(255,255,255,0.08) 0%, transparent 50%);
```

### LeadOS Brand Tokens
```css
--brand-green: #00A86B;
--brand-green-light: #E8F8F2;
--bg: #F8F8F6;
--card-bg: #FFFFFF;
--text-primary: #1A1A1A;
--text-secondary: #6B6B6B;
--font: 'DM Sans', sans-serif;
--font-heading: 'Playfair Display', serif;
--radius: 10px;
--hot: #E24B4A;
--warm: #BA7517;
--cool: #888780;
```

### Rules
- **Light mode** for LeadOS (dark mode for PeakClaw)
- Bento Grid layouts — never standard equal columns
- Playfair Display for headings, DM Sans for body
- Generous negative space — padding-y minimum 5rem on all sections
- 0.3s ease-in-out hover glow on all primary buttons
- Dark mode + 1-2% noise texture overlay on any dark surfaces
- NO generic purple gradients, NO Inter/Roboto/Arial, NO template patterns

---

## 6. SUPABASE SCHEMA — RUN THIS MIGRATION FIRST

Open Supabase SQL Editor and run:

```sql
-- LeadOS Personal Mode: leads table
create table if not exists leads (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),

  -- Raw scrape data
  source text not null,
  raw_name text,
  raw_contact text,
  raw_text text,
  location text default 'Austin, TX',

  -- Claude enrichment
  insurance_type text,
  urgency_score integer check (urgency_score between 1 and 10),
  carrier_recommendation text,
  outreach_message text,
  enrichment_reasoning text,

  -- Agent workflow
  status text default 'new',
  agent_notes text,
  quoted_premium numeric,

  -- Metadata
  apify_run_id text,
  enriched_at timestamptz
);

create index if not exists leads_status_idx on leads(status);
create index if not exists leads_created_idx on leads(created_at desc);
create index if not exists leads_urgency_idx on leads(urgency_score desc);
alter table leads enable row level security;

-- Users / agents table
create table if not exists users (
  id uuid primary key references auth.users(id),
  created_at timestamptz default now(),
  email text unique not null,
  full_name text,
  plan text default 'lone_wolf',
  stripe_customer_id text,
  stripe_subscription_id text,
  agency_name text,
  is_active boolean default true
);

-- Campaigns table
create table if not exists campaigns (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  user_id uuid references users(id),
  name text not null,
  industry text default 'insurance',
  target_location text,
  status text default 'active',
  leads_generated integer default 0,
  closes integer default 0
);

-- Skills usage log
create table if not exists skill_runs (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  user_id uuid references users(id),
  skill_name text,
  input_data jsonb,
  output_data jsonb,
  tokens_used integer
);
```

---

## 7. APIFY SCRAPER SERVICE

**File:** `services/apify_scraper.py`

```python
import httpx
import asyncio
import os
from typing import List, Dict

APIFY_BASE = "https://api.apify.com/v2"
APIFY_TOKEN = os.environ["APIFY_API_TOKEN"]

# Actor configs
FB_MARKETPLACE_CONFIG = {
    "searchQuery": "car",
    "location": "Austin, TX",
    "maxItems": 30,
    "priceMax": 25000
}

CRAIGSLIST_CONFIG = {
    "startUrls": [{"url": "https://austin.craigslist.org/search/apa"}],
    "maxItems": 40,
    "includeContactInfo": True
}

REDDIT_CONFIG = {
    "startUrls": [
        {"url": "https://www.reddit.com/r/Austin/search/?q=moving+to+austin&sort=new"},
        {"url": "https://www.reddit.com/r/Austin/search/?q=just+moved&sort=new"}
    ],
    "maxItems": 20
}

async def run_actor(actor_id: str, run_input: dict) -> List[Dict]:
    async with httpx.AsyncClient(timeout=120) as client:
        run_resp = await client.post(
            f"{APIFY_BASE}/acts/{actor_id}/runs",
            params={"token": APIFY_TOKEN},
            json={"runInput": run_input}
        )
        run_resp.raise_for_status()
        run_id = run_resp.json()["data"]["id"]

        for _ in range(18):
            await asyncio.sleep(5)
            status_resp = await client.get(
                f"{APIFY_BASE}/acts/{actor_id}/runs/{run_id}",
                params={"token": APIFY_TOKEN}
            )
            status = status_resp.json()["data"]["status"]
            if status == "SUCCEEDED":
                break
            if status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                return []

        dataset_id = status_resp.json()["data"]["defaultDatasetId"]
        items_resp = await client.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={"token": APIFY_TOKEN, "limit": 50}
        )
        return items_resp.json()

async def scrape_all_sources() -> List[Dict]:
    results = await asyncio.gather(
        run_actor("apify/facebook-marketplace-scraper", FB_MARKETPLACE_CONFIG),
        run_actor("apify/craigslist-scraper", CRAIGSLIST_CONFIG),
        run_actor("apify/reddit-scraper", REDDIT_CONFIG),
        return_exceptions=True
    )

    normalized = []

    if isinstance(results[0], list):
        for item in results[0]:
            normalized.append({
                "source": "facebook_marketplace",
                "raw_name": item.get("sellerName", "Unknown"),
                "raw_contact": item.get("sellerProfileUrl", ""),
                "raw_text": f"{item.get('title','')} — {item.get('description','')} — ${item.get('price','')}",
                "location": "Austin, TX"
            })

    if isinstance(results[1], list):
        for item in results[1]:
            normalized.append({
                "source": "apartment_listing",
                "raw_name": item.get("posterName", "Unknown"),
                "raw_contact": item.get("email", item.get("phone", "")),
                "raw_text": f"{item.get('title','')} — {item.get('body','')}",
                "location": item.get("neighborhood", "Austin, TX")
            })

    if isinstance(results[2], list):
        for item in results[2]:
            normalized.append({
                "source": "social_post",
                "raw_name": item.get("author", "Unknown"),
                "raw_contact": f"reddit.com/u/{item.get('author','')}",
                "raw_text": f"{item.get('title','')} — {item.get('body','')}",
                "location": "Austin, TX"
            })

    return normalized
```

---

## 8. CLAUDE ENRICHMENT LAYER

**File:** `services/enrichment.py`

```python
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
        message = client.messages.create(
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
        result = json.loads(message.content[0].text)
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
```

---

## 9. FASTAPI ROUTES

**File:** `routers/leads.py`

```python
from fastapi import APIRouter, BackgroundTasks, HTTPException
from supabase import create_client
import os
from services.apify_scraper import scrape_all_sources
from services.enrichment import enrich_all_leads
from datetime import datetime

router = APIRouter(prefix="/api/leads", tags=["leads"])
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

@router.post("/run-scrape")
async def run_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(scrape_enrich_save)
    return {"status": "running", "message": "Lead scrape started. Check /api/leads in ~2 minutes."}

async def scrape_enrich_save():
    raw_leads = await scrape_all_sources()
    enriched_leads = await enrich_all_leads(raw_leads)
    for lead in enriched_leads:
        supabase.table("leads").insert({
            "source": lead.get("source"),
            "raw_name": lead.get("raw_name"),
            "raw_contact": lead.get("raw_contact"),
            "raw_text": lead.get("raw_text", "")[:1000],
            "location": lead.get("location", "Austin, TX"),
            "insurance_type": lead.get("insurance_type"),
            "urgency_score": lead.get("urgency_score"),
            "carrier_recommendation": lead.get("carrier_recommendation"),
            "outreach_message": lead.get("outreach_message"),
            "enrichment_reasoning": lead.get("enrichment_reasoning"),
            "status": "new",
            "enriched_at": datetime.utcnow().isoformat()
        }).execute()

@router.get("/")
async def get_leads(status: str = None, min_urgency: int = 1):
    query = supabase.table("leads").select("*").gte("urgency_score", min_urgency).order("urgency_score", desc=True)
    if status:
        query = query.eq("status", status)
    result = query.execute()
    return {"leads": result.data, "count": len(result.data)}

@router.patch("/{lead_id}/status")
async def update_status(lead_id: str, status: str, agent_notes: str = None, quoted_premium: float = None):
    valid = ["new", "contacted", "quoted", "closed", "not_interested"]
    if status not in valid:
        raise HTTPException(400, f"Status must be one of: {valid}")
    update_data = {"status": status}
    if agent_notes:
        update_data["agent_notes"] = agent_notes
    if quoted_premium:
        update_data["quoted_premium"] = quoted_premium
    supabase.table("leads").update(update_data).eq("id", lead_id).execute()
    return {"success": True}

@router.get("/stats")
async def get_stats():
    all_leads = supabase.table("leads").select("status, urgency_score, insurance_type").execute().data
    return {
        "total": len(all_leads),
        "new": len([l for l in all_leads if l["status"] == "new"]),
        "contacted": len([l for l in all_leads if l["status"] == "contacted"]),
        "quoted": len([l for l in all_leads if l["status"] == "quoted"]),
        "closed": len([l for l in all_leads if l["status"] == "closed"]),
        "hot_leads": len([l for l in all_leads if l.get("urgency_score", 0) >= 8]),
        "by_type": {
            "auto": len([l for l in all_leads if l.get("insurance_type") == "auto"]),
            "renters": len([l for l in all_leads if l.get("insurance_type") == "renters"]),
            "bundle": len([l for l in all_leads if l.get("insurance_type") == "bundle"])
        }
    }
```

---

## 10. HEARTBEAT SCHEDULER — DAILY 7AM AUTO-RUN

**File:** `services/scheduler.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.apify_scraper import scrape_all_sources
from services.enrichment import enrich_all_leads
from supabase import create_client
import os, pytz
from datetime import datetime

scheduler = AsyncIOScheduler(timezone=pytz.timezone("America/Chicago"))
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

@scheduler.scheduled_job("cron", hour=7, minute=0)
async def morning_lead_drop():
    print("[LeadOS Heartbeat] 7am lead drop starting...")
    raw = await scrape_all_sources()
    enriched = await enrich_all_leads(raw)
    for lead in enriched:
        supabase.table("leads").insert({
            "source": lead.get("source"),
            "raw_name": lead.get("raw_name"),
            "raw_contact": lead.get("raw_contact"),
            "raw_text": lead.get("raw_text", "")[:1000],
            "location": lead.get("location", "Austin, TX"),
            "insurance_type": lead.get("insurance_type"),
            "urgency_score": lead.get("urgency_score"),
            "carrier_recommendation": lead.get("carrier_recommendation"),
            "outreach_message": lead.get("outreach_message"),
            "status": "new",
            "enriched_at": datetime.utcnow().isoformat()
        }).execute()
    print(f"[LeadOS Heartbeat] Done. {len(enriched)} leads saved.")

# Wire into main.py:
# from services.scheduler import scheduler
# @app.on_event("startup")
# async def start_scheduler():
#     scheduler.start()
```

---

## 11. AGENT COMMAND DASHBOARD

**File:** `src/pages/Dashboard.jsx`

Build a full-page Agent Command Dashboard. Use the LeadOS brand tokens from Section 5.

### Layout:
```
┌─────────────────────────────────────────────────────┐
│  LeadOS  [🟢 Run New Scrape]   Stats bar            │
├─────────────────────────────────────────────────────┤
│  Filter: [All][New][Contacted][Quoted][Closed]       │
│  Type: [All][Auto][Renters][Bundle]  Sort: Urgency↓  │
├─────────────────────────────────────────────────────┤
│  Score | Name | Type | Carrier | Script | Status    │
└─────────────────────────────────────────────────────┘
```

### Requirements per lead row:
- Urgency badge: 8-10 = red, 5-7 = amber, 1-4 = gray
- Insurance type pill: 🚗 Auto | 🏠 Renters | 📦 Bundle
- Outreach message: first 60 chars + `[📋 Copy]` button → clipboard toast
- Status dropdown: inline select → PATCH on change
- Row hover: subtle #F0FAF5 green tint

### API calls:
```javascript
const API = process.env.REACT_APP_API_URL
GET    ${API}/api/leads
GET    ${API}/api/leads/stats
POST   ${API}/api/leads/run-scrape
PATCH  ${API}/api/leads/${id}/status?status=contacted
```

---

## 12. REQUIREMENTS.TXT ADDITIONS

Add these if not already present:
```
apscheduler==3.10.4
pytz==2024.1
httpx==0.27.0
anthropic>=0.25.0
supabase>=2.0.0
apify-client>=1.7.0
```

---

## 13. MAIN.PY WIRING CHECKLIST

In your `main.py`, confirm these are all wired:
```python
# Routers
from routers.leads import router as leads_router
app.include_router(leads_router)

# Scheduler startup
from services.scheduler import scheduler
@app.on_event("startup")
async def start_scheduler():
    scheduler.start()

# CORS — allow Netlify domain
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tryleados.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 14. BUILD ORDER — EXECUTE IN THIS EXACT SEQUENCE

```
1.  Confirm MOCK_MODE=false in Railway variables
2.  Run Supabase migration (Section 6) in SQL Editor
3.  Create services/apify_scraper.py (Section 7)
4.  Create services/enrichment.py (Section 8)
5.  Create routers/leads.py (Section 9)
6.  Wire leads router into main.py
7.  Create services/scheduler.py (Section 10)
8.  Wire scheduler into main.py startup (Section 13)
9.  Add CORS middleware to main.py (Section 13)
10. pip install -r requirements.txt (Section 12)
11. Deploy to Railway → verify /api/leads/run-scrape returns 200
12. Create src/pages/Dashboard.jsx (Section 11)
13. Set REACT_APP_API_URL in Netlify env vars → Railway URL
14. Deploy frontend → verify dashboard loads
15. Hit "Run Scrape" → wait 2 min → verify leads appear
```

---

## 15. FIRST RUN VALIDATION CHECKLIST

After build, confirm ALL of these:
- [ ] `POST /api/leads/run-scrape` → `{"status": "running"}`
- [ ] Wait 2 min → `GET /api/leads` returns 10+ lead objects
- [ ] Each lead has `urgency_score`, `outreach_message`, `carrier_recommendation`
- [ ] Dashboard loads at tryleados.com
- [ ] Copy button works and shows toast
- [ ] Status dropdown updates persist on page refresh
- [ ] Stats bar shows correct counts
- [ ] Scheduler logs "7am lead drop" in Railway logs at 7am CT

---

## 16. KNOWN ISSUES — CHECK THESE IF SOMETHING BREAKS

| Issue | Fix |
|-------|-----|
| Netlify 404 on refresh | Add `_redirects` file: `/* /index.html 200` |
| Railway crash on start | Check start command: `python main.py` or `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Cloudflare blocking scripts | Disable Cloudflare proxy for Railway subdomain |
| Apify actor fails | Log error, continue with other sources — never crash pipeline |
| Claude JSON parse error | Strip markdown fences before `json.loads()` |
| CORS error from Netlify | Add `https://tryleados.com` to allow_origins in main.py |
| GitHub filename conflicts | Never number files on repeated downloads — overwrite same filename |

---

## 17. TWO-CLAUDE WORKFLOW

- **claude.ai (architecture session)** → Strategy, specs, CLAUDE.md updates, pitch materials
- **Claude Code (this file)** → Live repo execution against actual codebase

This file is the bridge. Update it whenever the architecture changes.
Claude Code reads it fresh on every session — no re-explaining needed.

---

*LeadOS — Built by Enrique Saucedo | We Insure / PEAK6 | Austin, TX*
*PEAK6 Trials Deadline: May 29, 2026*

## GStack Skills Active
Use /browse skill from gstack for all web browsing.
Never use mcp__claude-in-chrome__* tools.

Available skills:
/office-hours - CEO mode: reframe problems before coding
/plan - Eng Manager: lock architecture decisions
/design-shotgun - Designer: catch AI slop in UI
/review - Senior reviewer: find production bugs
/ship - Release engineer: PR and deploy
/qa - QA lead: browser testing
/security - Security officer: OWASP audits
