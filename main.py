"""
LeadOS - Ultimate Lead Intelligence OS
AI Agent Infrastructure Entry Point
"""

import asyncio
import logging
import os
from core.orchestrator import AgentOrchestrator
from core.config import LeadOSConfig
from api.server import start_api_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
log = logging.getLogger("LeadOS")


async def main():
    log.info("🚀 LeadOS Agent Infrastructure starting...")

    config = LeadOSConfig.from_env()
    orchestrator = AgentOrchestrator(config)

    await orchestrator.initialize()
    log.info("✅ All agents initialized and ready.")

    # Start API server + agent loop concurrently
    await asyncio.gather(
        start_api_server(orchestrator, host="0.0.0.0", port=int(os.environ.get("PORT", 8000))),
        orchestrator.run_forever(),
    )


if __name__ == "__main__":
    asyncio.run(main())
