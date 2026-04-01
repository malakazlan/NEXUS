"""Resource manager — token budgets and cost tracking."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class AgentUsage:
    """Token usage for a single agent."""
    agent_id: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    budget: int = 100_000
    calls: int = 0
    last_call: datetime | None = None

    @property
    def remaining(self) -> int:
        return max(0, self.budget - self.total_tokens)

    @property
    def exceeded(self) -> bool:
        return self.total_tokens >= self.budget


class ResourceManager:
    """Tracks per-agent and global token usage."""

    def __init__(self, global_budget: int = 1_000_000) -> None:
        self._agents: dict[str, AgentUsage] = {}
        self._global_budget = global_budget
        self._global_used = 0

    def init_agent(self, agent_id: str, budget: int = 100_000) -> AgentUsage:
        usage = AgentUsage(agent_id=agent_id, budget=budget)
        self._agents[agent_id] = usage
        return usage

    def record_usage(
        self,
        agent_id: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> AgentUsage:
        usage = self._agents.get(agent_id)
        if usage is None:
            usage = self.init_agent(agent_id)

        usage.prompt_tokens += prompt_tokens
        usage.completion_tokens += completion_tokens
        usage.total_tokens += prompt_tokens + completion_tokens
        usage.calls += 1
        usage.last_call = datetime.now(timezone.utc)

        self._global_used += prompt_tokens + completion_tokens

        logger.debug(
            "Usage: agent=%s tokens=%d/%d (global=%d/%d)",
            agent_id,
            usage.total_tokens,
            usage.budget,
            self._global_used,
            self._global_budget,
        )
        return usage

    def check_budget(self, agent_id: str) -> bool:
        """Return True if agent is within budget."""
        usage = self._agents.get(agent_id)
        if usage is None:
            return True
        return not usage.exceeded

    def get_usage(self, agent_id: str) -> AgentUsage | None:
        return self._agents.get(agent_id)

    def get_global_usage(self) -> dict:
        return {
            "total_tokens": self._global_used,
            "budget": self._global_budget,
            "remaining": max(0, self._global_budget - self._global_used),
            "agents": len(self._agents),
        }

    def remove_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)
