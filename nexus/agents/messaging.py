"""Agent-to-agent messaging (IPC) via the EventBus."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from uuid import uuid4

from pydantic import BaseModel, Field

from nexus.events.bus import EventBus
from nexus.events.types import EventType, NexusEvent

logger = logging.getLogger(__name__)

MessageHandler = Callable[["AgentMessage"], Coroutine[Any, Any, None]]


class AgentMessage(BaseModel):
    """A message sent between agents."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    from_agent: str
    to_agent: str
    content: str
    message_type: str = "request"
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"frozen": True}


class MessageRouter:
    """Routes messages between agents using the EventBus."""

    def __init__(self, event_bus: EventBus) -> None:
        self._bus = event_bus
        self._handlers: dict[str, MessageHandler] = {}
        self._bus.subscribe(EventType.AGENT_MESSAGE, self._dispatch)

    def register_handler(self, agent_id: str, handler: MessageHandler) -> None:
        self._handlers[agent_id] = handler

    def unregister_handler(self, agent_id: str) -> None:
        self._handlers.pop(agent_id, None)

    async def send(
        self,
        *,
        from_agent: str,
        to_agent: str,
        content: str,
        message_type: str = "request",
        correlation_id: str | None = None,
    ) -> AgentMessage:
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            correlation_id=correlation_id,
        )
        await self._bus.emit(
            NexusEvent(
                type=EventType.AGENT_MESSAGE,
                source=from_agent,
                data=msg.model_dump(mode="json"),
            )
        )
        return msg

    async def broadcast(
        self,
        *,
        from_agent: str,
        content: str,
    ) -> AgentMessage:
        return await self.send(
            from_agent=from_agent,
            to_agent="*",
            content=content,
            message_type="broadcast",
        )

    async def _dispatch(self, event: NexusEvent) -> None:
        msg = AgentMessage(**event.data)

        if msg.to_agent == "*":
            for agent_id, handler in self._handlers.items():
                if agent_id != msg.from_agent:
                    try:
                        await handler(msg)
                    except Exception as e:
                        logger.error("Message handler error for %s: %s", agent_id, e)
        else:
            handler = self._handlers.get(msg.to_agent)
            if handler:
                try:
                    await handler(msg)
                except Exception as e:
                    logger.error("Message handler error for %s: %s", msg.to_agent, e)
            else:
                logger.warning("No handler for agent %s, message dropped", msg.to_agent)
