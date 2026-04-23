"""LeadOS"""
import os
import asyncio
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LeadOS")
log.info("=== LEADOS leadOS/main.py LOADING ===")

app = FastAPI(title="LeadOS", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
log.info(f"=== APP DEFINED: {app} ===")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.1.0"}


@app.on_event("startup")
async def startup():
    log.info("=== STARTUP EVENT FIRED ===")
    try:
        from core.config import LeadOSConfig
        from core.orchestrator import AgentOrchestrator
        from api.server import build_routes

        cfg = LeadOSConfig.from_env()
        orch = AgentOrchestrator(cfg)
        # Register routes immediately so /health is available before agents init
        build_routes(app, orch)
        app.state.orchestrator = orch
        log.info("=== ROUTES REGISTERED — agents booting in background ===")

        async def _boot_agents():
            try:
                await orch.initialize()
                asyncio.create_task(orch.run_forever())
                log.info("=== ALL AGENTS READY ===")
            except Exception as e:
                log.error(f"=== AGENT BOOT FAILED: {e} ===", exc_info=True)

        asyncio.create_task(_boot_agents())
    except Exception as e:
        log.error(f"=== STARTUP FAILED: {e} ===", exc_info=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0",
                port=int(os.environ.get("PORT", 8000)))
