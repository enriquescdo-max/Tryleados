"""
LeadOS - Ultimate Lead Intelligence OS
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
log = logging.getLogger("LeadOS")

_boot_error = None
_orchestrator = None

try:
    from core.config import LeadOSConfig
    from core.orchestrator import AgentOrchestrator
    _config = LeadOSConfig.from_env()
    _orchestrator = AgentOrchestrator(_config)
    log.info("Orchestrator created OK")
except Exception as e:
    _boot_error = e
    log.error(f"BOOT ERROR: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if _orchestrator:
        log.info("LeadOS starting agents...")
        await _orchestrator.initialize()
        log.info("All agents ready.")
        task = asyncio.create_task(_orchestrator.run_forever())
        yield
        task.cancel()
    else:
        log.error(f"Skipping agent init — boot failed: {_boot_error}")
        yield


app = FastAPI(title="LeadOS", version="3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    if _boot_error:
        return {"status": "boot_error", "error": str(_boot_error)}
    return {
        "status": "ok",
        "version": "3.0",
        "agents": len(_orchestrator.agents) if _orchestrator else 0,
    }


if _orchestrator:
    try:
        from api.server import build_routes
        build_routes(app, _orchestrator)
        log.info("Routes registered.")
    except Exception as e:
        log.error(f"ROUTE ERROR: {e}", exc_info=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
    )
