"""Human-in-the-loop approval gate.

When an action requires approval (e.g., tool creation), an approval.requested
event is emitted and the caller awaits the response. The CLI or dashboard
listens for these events and prompts the user.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from nexus.events.bus import EventBus
from nexus.events.types import EventType, NexusEvent

logger = logging.getLogger(__name__)


class ApprovalGate:
    """Manages human approval requests and responses.

    Usage:
        approved = await gate.request(
            action="tool.create",
            description="Create csv_parser tool",
            details={...},
            source="coder-abc123",
        )
        if approved:
            # proceed
    """

    def __init__(self, event_bus: EventBus, *, auto_approve: bool = False) -> None:
        self._bus = event_bus
        self._auto_approve = auto_approve
        self._pending: dict[str, asyncio.Future[bool]] = {}

        # Listen for approval responses
        self._bus.subscribe(EventType.APPROVAL_GRANTED, self._on_granted)
        self._bus.subscribe(EventType.APPROVAL_DENIED, self._on_denied)

    async def request(
        self,
        *,
        action: str,
        description: str,
        details: dict[str, Any] | None = None,
        source: str = "kernel",
        timeout: float = 300.0,
    ) -> bool:
        """Request human approval. Blocks until approved/denied or timeout.

        Returns True if approved, False if denied or timed out.
        """
        if self._auto_approve:
            logger.info("Auto-approving: %s — %s", action, description)
            return True

        # Create a future to await the response
        loop = asyncio.get_event_loop()
        future: asyncio.Future[bool] = loop.create_future()

        event = NexusEvent(
            type=EventType.APPROVAL_REQUESTED,
            source=source,
            data={
                "action": action,
                "description": description,
                "details": details or {},
            },
        )

        self._pending[event.id] = future

        # Emit the request event
        await self._bus.emit(event)
        logger.info("Approval requested [%s]: %s — %s", event.id, action, description)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Approval request %s timed out after %.0fs", event.id, timeout)
            self._pending.pop(event.id, None)
            return False

    async def respond(self, request_id: str, approved: bool) -> None:
        """Respond to a pending approval request (called by CLI/dashboard)."""
        if approved:
            await self._bus.emit(
                NexusEvent(
                    type=EventType.APPROVAL_GRANTED,
                    source="human",
                    data={"request_id": request_id},
                )
            )
        else:
            await self._bus.emit(
                NexusEvent(
                    type=EventType.APPROVAL_DENIED,
                    source="human",
                    data={"request_id": request_id},
                )
            )

    async def _on_granted(self, event: NexusEvent) -> None:
        request_id = event.data.get("request_id", "")
        future = self._pending.pop(request_id, None)
        if future and not future.done():
            future.set_result(True)
            logger.info("Approval granted: %s", request_id)

    async def _on_denied(self, event: NexusEvent) -> None:
        request_id = event.data.get("request_id", "")
        future = self._pending.pop(request_id, None)
        if future and not future.done():
            future.set_result(False)
            logger.info("Approval denied: %s", request_id)
