"""FastAPI application — REST API + WebSocket for NEXUS."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nexus.api.routes import agents as agents_routes
from nexus.api.routes import memory as memory_routes
from nexus.api.routes import tasks as tasks_routes
from nexus.api.routes import tools as tools_routes
from nexus.api.websocket import broadcast_event, router as ws_router
from nexus.kernel.kernel import Kernel

logger = logging.getLogger(__name__)

# Module-level kernel reference
kernel: Kernel | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Boot the kernel on startup, shut down on exit."""
    global kernel
    kernel = Kernel()
    await kernel.boot()

    # Wire routes to the kernel
    tasks_routes.init(kernel)
    agents_routes.init(kernel)
    tools_routes.init(kernel)
    memory_routes.init(kernel)

    # Subscribe WebSocket broadcaster to all events
    kernel.event_bus.subscribe("*", broadcast_event)

    logger.info("NEXUS API ready on port %d", kernel.config.api_port)
    yield

    await kernel.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="NEXUS API",
        description="Self-Evolving Multi-Agent Operating System",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routes
    app.include_router(tasks_routes.router, prefix="/api")
    app.include_router(agents_routes.router, prefix="/api")
    app.include_router(tools_routes.router, prefix="/api")
    app.include_router(memory_routes.router, prefix="/api")
    app.include_router(ws_router, prefix="/api")

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "version": "0.1.0",
            "agents": kernel.agent_registry.count() if kernel else 0,
            "tools": len(kernel.tool_registry.list_tools()) if kernel else 0,
        }

    @app.get("/api/events")
    async def recent_events(limit: int = 50) -> list[dict]:
        if kernel is None:
            return []
        events = kernel.event_bus.get_history(limit=limit)
        return [
            {
                "id": e.id,
                "type": e.type.value,
                "source": e.source,
                "data": e.data,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]

    return app
