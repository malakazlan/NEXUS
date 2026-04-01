"""Agent registry — tracks all agent instances and their metadata."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexus.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Tracks running agents by id, type, and capabilities."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.id] = agent
        logger.info("Agent registered: %s (%s)", agent.id, agent.type)

    def unregister(self, agent_id: str) -> BaseAgent | None:
        agent = self._agents.pop(agent_id, None)
        if agent:
            logger.info("Agent unregistered: %s", agent_id)
        return agent

    def get(self, agent_id: str) -> BaseAgent | None:
        return self._agents.get(agent_id)

    def list_all(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def find_by_type(self, agent_type: str) -> list[BaseAgent]:
        return [a for a in self._agents.values() if a.type == agent_type]

    def find_by_capability(self, capability: str) -> list[BaseAgent]:
        return [a for a in self._agents.values() if capability in a.capabilities]

    def count(self) -> int:
        return len(self._agents)

    def clear(self) -> None:
        self._agents.clear()
