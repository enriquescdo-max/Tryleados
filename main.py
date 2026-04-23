"""
LeadOS - Ultimate Lead Intelligence OS
AI Agent Infrastructure Entry Point
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.orchestrator import AgentOrchestrator
from core.config import LeadOSConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
log = logging.getLogger("LeadOS")

config = LeadOSConfig.from_env()
orchestrator = AgentOrchestrator(config)
_agent_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent_task
    log.info("LeadOS starting...")
    await orchestrator.initialize()
    log.info("All agents initialized.")
    _agent_task = asyncio.create_task(orchestrator.run_forever())
    yield
    if _agent_task:
        _agent_task.cancel()


app = FastAPI(title="LeadOS", version="3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routes from api/server by importing the router builder
from api.server import build_routes
build_routes(app, orchestrator)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=False)
