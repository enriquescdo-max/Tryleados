# ⚡ LeadOS — The Operating System for Leads

> Autonomous AI agents that find, qualify, enrich, and engage your ideal customers — 24/7, across every industry.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LEADOS PLATFORM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌──────────────────────────────────────┐   │
│  │  Dashboard  │    │           AGENT ORCHESTRATOR          │   │
│  │  (React UI) │◄──►│  Priority Queue · Task Router        │   │
│  └─────────────┘    │  Retry Logic · Chain Automation       │   │
│         │           └──────────┬───────────────────────────┘   │
│  ┌──────▼──────┐               │                               │
│  │  FastAPI    │    ┌──────────▼───────────────────────────┐   │
│  │  REST + WS  │    │           AI AGENT FLEET              │   │
│  └─────────────┘    │                                       │   │
│                     │  🕷️ SCOUT    Web crawler & discovery  │   │
│                     │  💼 INTEL    LinkedIn & enrichment    │   │
│                     │  ⚡ SIGNAL   Buying intent detection  │   │
│                     │  🧠 QUALIFY  AI lead scoring (0-100)  │   │
│                     │  ✉️ REACH    Personalized outreach    │   │
│                     │  📊 LEARN    Self-improvement engine  │   │
│                     └──────────┬───────────────────────────┘   │
│                                │                               │
│              ┌─────────────────┼─────────────────┐            │
│              ▼                 ▼                 ▼            │
│       ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│       │  PostgreSQL  │  │    Redis    │  │  Claude AI  │      │
│       │  Lead Store  │  │  Job Queue  │  │  (Brain)    │      │
│       └─────────────┘  └─────────────┘  └─────────────┘      │
│                                                                 │
│       ┌──────────────────────────────────────────────────┐    │
│       │              INTEGRATIONS LAYER                   │    │
│       │  HubSpot · Salesforce · Pipedrive · Gmail        │    │
│       │  LinkedIn API · Crunchbase · SendGrid · Slack    │    │
│       └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agent Fleet

| Agent | Role | Key Capability |
|-------|------|----------------|
| 🕷️ **SCOUT** | Discovery | Crawls web, G2, Crunchbase, job boards for target companies |
| 💼 **INTEL** | Enrichment | Maps org charts, finds decision-makers, verifies emails |
| ⚡ **SIGNAL** | Intent | Detects funding, hiring, leadership changes as buy signals |
| 🧠 **QUALIFY** | Scoring | Scores leads 0-100 with explainable AI reasoning |
| ✉️ **REACH** | Outreach | Writes hyper-personalized emails using real context |
| 📊 **LEARN** | Improvement | Self-trains on won/lost deals to improve all agents |

---

## 🔄 Automated Pipeline Flow

```
User defines ICP
      │
      ▼
SCOUT agent discovers companies matching ICP
      │
      ▼ (auto-chained)
INTEL agent enriches each company with contacts + tech stack
      │
      ▼ (parallel)
SIGNAL agent scores buying intent
      │
      ▼
QUALIFY agent scores lead 0-100 vs ICP
      │
      ├── Score < 70 → Archive (not a fit)
      │
      └── Score ≥ 70 → REACH agent writes personalized email
                              │
                              ▼
                        Email sent → CRM synced → Pipeline updated
                              │
                              ▼
                        LEARN agent records outcome → improves model
```

---

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/yourco/leadOS
cd leadOS
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY and other keys
```

### 3. Start the Server
```bash
cd api
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Run Your First Campaign (API)
```bash
curl -X POST http://localhost:8000/campaigns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q1 SaaS Outbound",
    "icp": {
      "industry": "SaaS",
      "company_size": "50-500",
      "location": "North America",
      "seniority_target": ["vp", "director", "c_suite"]
    },
    "daily_lead_target": 50,
    "auto_outreach": false
  }'
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System status + agent stats |
| POST | `/campaigns` | Launch a new lead gen campaign |
| GET | `/campaigns` | List all campaigns |
| POST | `/agent/command` | Natural language agent command |
| GET | `/leads` | Get qualified leads (with filters) |
| POST | `/leads/{id}/qualify` | Re-qualify a lead |
| POST | `/leads/{id}/enrich` | Re-enrich a lead |
| POST | `/outreach/generate` | Generate personalized email |
| GET | `/analytics/overview` | Dashboard metrics |
| WS | `/ws/feed` | Real-time agent activity stream |

---

## 🗂️ Project Structure

```
leadOS/
├── agents/
│   └── agents.py          # All 6 AI agents
├── core/
│   └── orchestrator.py    # Task queue & agent routing
├── api/
│   └── server.py          # FastAPI REST + WebSocket server
├── db/
│   ├── models.py          # SQLAlchemy models (leads, campaigns)
│   └── migrations/        # Alembic migrations
├── integrations/
│   ├── hubspot.py
│   ├── salesforce.py
│   ├── sendgrid.py
│   └── linkedin.py
├── config/
│   └── settings.py        # Pydantic settings
├── requirements.txt
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Brain | Claude (Anthropic) |
| Backend | FastAPI + Python 3.11+ |
| Task Queue | Redis + asyncio |
| Database | PostgreSQL + SQLAlchemy |
| Web Scraping | Playwright + BeautifulSoup |
| Email | SendGrid |
| Auth | JWT + OAuth2 |
| Frontend | React + Tailwind |
| Deployment | Docker + AWS/GCP |

---

## 📈 Roadmap

### Phase 1 (MVP) ✅
- [x] Agent orchestrator
- [x] Scout, Intel, Qualify, Reach agents
- [x] FastAPI backend
- [x] Dashboard UI

### Phase 2 (Growth)
- [ ] PostgreSQL persistent storage
- [ ] CRM integrations (HubSpot, Salesforce)
- [ ] Multi-tenant SaaS architecture
- [ ] Stripe billing integration
- [ ] Chrome extension

### Phase 3 (Scale)
- [ ] White-label offering
- [ ] API marketplace
- [ ] Custom agent training per customer
- [ ] Mobile app
- [ ] Zapier integration

---

## 💰 SaaS Business Model

| Plan | Price | Leads/mo | Agents |
|------|-------|----------|--------|
| Starter | $49/mo | 500 | 2 |
| Pro | $149/mo | 5,000 | 6 |
| Enterprise | Custom | Unlimited | Custom |

**Unit Economics Target:**
- CAC: <$200
- LTV: >$2,400 (avg 16mo retention)
- LTV:CAC ratio: >12x
- Gross Margin: ~80%

---

*Built with ⚡ LeadOS — The Operating System for Leads*
