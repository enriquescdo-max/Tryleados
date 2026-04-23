"""
LeadOS - Ultimate Lead Intelligence OS
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
log = logging.getLogger("LeadOS")

# Boot orchestrator at module level so uvicorn main:app works
try:
    from core.config import LeadOSConfig
    from core.orchestrator import AgentOrchestrator
    _config = LeadOSConfig.from_env()
    _orchestrator = AgentOrchestrator(_config)
    log.info("Orchestrator created OK")
except Exception as _boot_err:
    log.error(f"BOOT ERROR: {_boot_err}", exc_info=True)
    # Still define app so uvicorn doesn't complain — returns 503 on every route
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/{path:path}")
    async def broken(path: str):
        return {"status": "boot_error", "error": str(_boot_err)}

    sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("LeadOS starting agents...")
    await _orchestrator.initialize()
    log.info("All agents ready.")
    task = asyncio.create_task(_orchestrator.run_forever())
    yield
    task.cancel()


app = FastAPI(title="LeadOS", version="3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from api.server import build_routes
    build_routes(app, _orchestrator)
    log.info("Routes registered.")
except Exception as _route_err:
    log.error(f"ROUTE ERROR: {_route_err}", exc_info=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
    )
