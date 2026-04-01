"""In-process async event bus (pub/sub)."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

from nexus.events.types import EventType, NexusEvent

logger = logging.getLogger(__name__)

# Subscriber callback signature
Subscriber = Callable[[NexusEvent], Coroutine[Any, Any, None]]


class EventBus:
    """Async pub/sub event bus.

    Subscribers register for specific event types (or '*' for all).
    Events are dispatched concurrently to all matching subscribers.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)
        self._history: list[NexusEvent] = []
        self._max_history: int = 1000

    def subscribe(self, event_type: EventType | str, callback: Subscriber) -> None:
        """Register *callback* for events of *event_type* (or '*' for all)."""
        key = event_type.value if isinstance(event_type, EventType) else event_type
        self._subscribers[key].append(callback)
        logger.debug("Subscriber registered for %s", key)

    def unsubscribe(self, event_type: EventType | str, callback: Subscriber) -> None:
        key = event_type.value if isinstance(event_type, EventType) else event_type
        try:
            self._subscribers[key].remove(callback)
        except ValueError:
            pass

    async def emit(self, event: NexusEvent) -> None:
        """Publish *event* to all matching subscribers."""
        # Store in history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        logger.debug("Event: %s from %s", event.type.value, event.source)

        # Collect matching subscribers
        targets: list[Subscriber] = []
        targets.extend(self._subscribers.get(event.type.value, []))
        targets.extend(self._subscribers.get("*", []))

        # Fire concurrently
        if targets:
            results = await asyncio.gather(
                *(cb(event) for cb in targets),
                return_exceptions=True,
            )
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        "Subscriber error for %s: %s",
                        event.type.value,
                        result,
                        exc_info=result,
                    )

    def get_history(self, event_type: EventType | str | None = None, limit: int = 50) -> list[NexusEvent]:
        """Return recent events, optionally filtered by type."""
        events = self._history
        if event_type is not None:
            key = event_type.value if isinstance(event_type, EventType) else event_type
            events = [e for e in events if e.type.value == key]
        return events[-limit:]

    def clear(self) -> None:
        self._subscribers.clear()
        self._history.clear()
