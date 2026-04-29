"""LeadOS API — stripped to essentials for Railway stability"""
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LeadOS")

app = FastAPI(title="LeadOS", version="3.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
try:
    from routers.carrier_scorer import router as carrier_scorer_router
    app.include_router(carrier_scorer_router)
    log.info("carrier_scorer loaded")
except Exception as e:
    log.warning(f"carrier_scorer failed: {e}")

try:
    from routers.campaigns import router as campaigns_router
    app.include_router(campaigns_router)
    log.info("campaigns loaded")
except Exception as e:
    log.warning(f"campaigns failed: {e}")

try:
    from routers.leads import router as leads_router
    app.include_router(leads_router)
    log.info("leads loaded")
except Exception as e:
    log.warning(f"leads failed: {e}")

try:
    from routers.outreach import router as outreach_router
    app.include_router(outreach_router)
    log.info("outreach loaded (HeyGen + Vapi + Instantly + Morning Brief)")
except Exception as e:
    log.warning(f"outreach failed: {e}")

# ── Also mount the original agent-based routes if available ──────────────────
try:
    from api.server import build_routes
    import asyncio
    from core.config import LeadOSConfig
    from core.orchestrator import AgentOrchestrator

    async def _boot():
        try:
            cfg = LeadOSConfig.from_env()
            orch = AgentOrchestrator(cfg)
            await asyncio.wait_for(orch.initialize(), timeout=20)
            build_routes(app, orch)
            asyncio.create_task(orch.run_forever())
            log.info("Agents ready")
        except Exception as e:
            log.warning(f"Agents skipped: {e}")

    @app.on_event("startup")
    async def startup():
        asyncio.create_task(_boot())

except Exception as e:
    log.warning(f"Agent system unavailable: {e}")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.2"}


@app.get("/")
async def root():
    return {"app": "LeadOS", "status": "running", "version": "3.2"}
