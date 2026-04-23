"""LeadOS"""
import os
import asyncio
import logging
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LeadOS")
log.info("=== LEADOS MAIN.PY LOADING ===")

app = FastAPI(title="LeadOS", version="3.0")
log.info(f"=== APP DEFINED: {app} ===")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "3.0"}


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
