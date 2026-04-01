"""Shared key-value state accessible by all agents."""

from __future__ import annotations

import logging
from typing import Any

from nexus.events.bus import EventBus
from nexus.events.types import EventType, NexusEvent

logger = logging.getLogger(__name__)


class SharedMemory:
    """In-memory KV store.  Every write emits a MEMORY_WRITE event."""

    def __init__(self, event_bus: EventBus) -> None:
        self._store: dict[str, Any] = {}
        self._bus = event_bus

    async def set(self, key: str, value: Any, *, source: str = "kernel") -> None:
        self._store[key] = value
        await self._bus.emit(
            NexusEvent(
                type=EventType.MEMORY_WRITE,
                source=source,
                data={"key": key, "value_type": type(value).__name__},
            )
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def keys(self) -> list[str]:
        return list(self._store.keys())

    def dump(self) -> dict[str, Any]:
        """Return a shallow copy of the entire store."""
        return dict(self._store)

    def clear(self) -> None:
        self._store.clear()
