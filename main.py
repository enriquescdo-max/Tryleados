"""LeadOS"""
import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("LeadOS")

log.info("main.py loading...")

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("LeadOS lifespan start")
    try:
        from core.config import LeadOSConfig
        from core.orchestrator import AgentOrchestrator
        cfg = LeadOSConfig.from_env()
        orch = AgentOrchestrator(cfg)
        app.state.orchestrator = orch
        await orch.initialize()
        log.info("Agents ready")
        task = asyncio.create_task(orch.run_forever())
        yield
        task.cancel()
    except Exception as e:
        log.error(f"Startup error: {e}", exc_info=True)
        app.state.orchestrator = None
        yield

app = FastAPI(title="LeadOS", version="3.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

log.info(f"app defined: {app}")

@app.get("/health")
async def health():
    orch = getattr(app.state, "orchestrator", None)
    if orch is None:
        return {"status": "starting_or_error"}
    return {"status": "ok", "version": "3.0", "agents": len(orch.agents)}

try:
    from api.server import build_routes
    orch_placeholder = None
    build_routes(app, orch_placeholder)
    log.info("Routes registered")
except Exception as e:
    log.error(f"Route registration error: {e}", exc_info=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
