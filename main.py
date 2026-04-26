"""LeadOS v3.1"""
import os
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LeadOS")
log.info("=== LEADOS MAIN.PY LOADING ===")

app = FastAPI(title="LeadOS", version="3.1")

# CORS — allow Netlify frontend + local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://tryleados.com",
        "https://tryleados.netlify.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static routers (always available, no agent deps) ─────────────────────────
from routers.carrier_scorer import router as carrier_scorer_router
from routers.leads import router as leads_router

app.include_router(carrier_scorer_router)
app.include_router(leads_router)

log.info(f"=== ROUTERS LOADED ===")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.1"}


@app.on_event("startup")
async def startup():
    log.info("=== STARTUP EVENT FIRED ===")
    try:
        from core.config import LeadOSConfig
        from core.orchestrator import AgentOrchestrator
        from api.server import build_routes

        cfg = LeadOSConfig.from_env()
        orch = AgentOrchestrator(cfg)
        await orch.initialize()
        build_routes(app, orch)
        asyncio.create_task(orch.run_forever())
        app.state.orchestrator = orch
        log.info("=== ALL AGENTS READY ===")
    except Exception as e:
        log.error(f"=== STARTUP FAILED: {e} ===", exc_info=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0",
                port=int(os.environ.get("PORT", 8000)))
