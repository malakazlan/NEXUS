"""WebSocket event streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from nexus.events.types import NexusEvent

logger = logging.getLogger(__name__)
router = APIRouter()

# Active WebSocket connections
_connections: set[WebSocket] = set()


async def broadcast_event(event: NexusEvent) -> None:
    """Push an event to all connected WebSocket clients."""
    if not _connections:
        return
    data = json.dumps({
        "id": event.id,
        "type": event.type.value,
        "source": event.source,
        "data": event.data,
        "timestamp": event.timestamp.isoformat(),
    })
    dead: list[WebSocket] = []
    for ws in _connections:
        try:
            await ws.send_text(data)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _connections.discard(ws)


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket) -> None:
    """Stream all NEXUS events to the client in real time."""
    await websocket.accept()
    _connections.add(websocket)
    logger.info("WebSocket client connected (%d total)", len(_connections))
    try:
        while True:
            # Keep alive — listen for client messages (e.g., ping)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(websocket)
        logger.info("WebSocket client disconnected (%d total)", len(_connections))
