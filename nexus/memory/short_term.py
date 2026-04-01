"""Per-agent short-term memory (conversation context)."""

from __future__ import annotations

from typing import Any


class ShortTermMemory:
    """Holds an agent's conversation messages for the current task.

    Implements a sliding window: when messages exceed *max_messages*,
    older messages (except the system prompt at index 0) are dropped.
    """

    def __init__(self, max_messages: int = 50) -> None:
        self._messages: list[dict[str, Any]] = []
        self._max: int = max_messages

    def add(self, role: str, content: str, **extra: Any) -> None:
        msg: dict[str, Any] = {"role": role, "content": content, **extra}
        self._messages.append(msg)
        self._trim()

    def get_messages(self) -> list[dict[str, Any]]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def _trim(self) -> None:
        if len(self._messages) <= self._max:
            return
        # Keep system message (index 0) + latest messages
        if self._messages and self._messages[0].get("role") == "system":
            system = self._messages[0]
            self._messages = [system] + self._messages[-(self._max - 1):]
        else:
            self._messages = self._messages[-self._max:]

    def __len__(self) -> int:
        return len(self._messages)
