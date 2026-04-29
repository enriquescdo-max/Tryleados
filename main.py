"""LeadOS v3.1"""
import os
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LeadOS")

app = FastAPI(title="LeadOS", version="3.1")

# CORS — allow Netlify frontend + local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carrier scorer and campaigns have zero external deps — always safe to load
try:
    from routers.carrier_scorer import router as carrier_scorer_router
    app.include_router(carrier_scorer_router)
    log.info("Carrier scorer router loaded")
except Exception as e:
    log.warning(f"Carrier scorer router failed: {e}")

try:
    from routers.campaigns import router as campaigns_router
    app.include_router(campaigns_router)
    log.info("Campaigns router loaded")
except Exception as e:
    log.warning(f"Campaigns router failed: {e}")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.1"}


# Load leads router immediately — no agent deps needed
try:
    from routers.leads import router as leads_router
    app.include_router(leads_router)
    log.info("Leads router loaded")
except Exception as e:
    log.warning(f"Leads router failed: {e}")


async def _boot_agents():
    """Boot agents in background — NEVER blocks startup or health check."""
    await asyncio.sleep(2)  # Let uvicorn fully start first
    try:
        from core.config import LeadOSConfig
        from core.orchestrator import AgentOrchestrator
        from api.server import build_routes

        cfg = LeadOSConfig.from_env()
        orch = AgentOrchestrator(cfg)
        try:
            await asyncio.wait_for(orch.initialize(), timeout=30)
        except asyncio.TimeoutError:
            log.warning("Agent init timed out — app still running")
            return
        build_routes(app, orch)
        asyncio.create_task(orch.run_forever())
        app.state.orchestrator = orch
        log.info("=== ALL AGENTS READY ===")
    except Exception as e:
        log.error(f"=== AGENT BOOT FAILED (non-fatal): {e} ===")
        # App continues running — leads API still works


@app.on_event("startup")
async def startup():
    log.info("=== STARTUP — booting agents in background ===")
    asyncio.create_task(_boot_agents())


# Start via: uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
