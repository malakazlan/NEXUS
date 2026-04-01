"""Agent factory — dynamic agent creation from specifications."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from nexus.agents.base import AgentStatus, BaseAgent, TaskResult
from nexus.kernel.scheduler import Task

if TYPE_CHECKING:
    from nexus.kernel.kernel import Kernel

logger = logging.getLogger(__name__)


class AgentSpec(BaseModel):
    """Specification for dynamically creating an agent."""

    type: str = "custom"
    role: str  # system prompt
    capabilities: list[str]
    tools: list[str] = []
    model: str | None = None
    token_budget: int = 100_000


class DynamicAgent(BaseAgent):
    """An agent created at runtime from an AgentSpec."""

    def __init__(self, kernel: Kernel, spec: AgentSpec) -> None:
        super().__init__(
            kernel=kernel,
            agent_type=spec.type,
            capabilities=spec.capabilities,
            tools=spec.tools,
            model=spec.model,
            system_prompt=spec.role,
            token_budget=spec.token_budget,
        )

    async def run(self, task: Task) -> TaskResult:
        self.status = AgentStatus.RUNNING
        logger.info("Dynamic agent %s (%s) working on: %s", self.id, self.type, task.description)

        try:
            self._memory.clear()
            self._memory.add("system", self.system_prompt)
            self._memory.add("user", task.description)

            response = await self.llm_call()
            content = await self.process_tool_calls(response)

            if content is None:
                content = response.choices[0].message.content or ""  # type: ignore[union-attr]

            self.status = AgentStatus.COMPLETED
            return TaskResult(success=True, output=content)

        except Exception as e:
            logger.error("Dynamic agent %s failed: %s", self.id, e, exc_info=True)
            self.status = AgentStatus.FAILED
            return TaskResult(success=False, error=str(e))


async def create_agent(kernel: Kernel, spec: AgentSpec) -> BaseAgent:
    """Create and spawn an agent from a spec."""
    agent = DynamicAgent(kernel, spec)
    await kernel.spawn_agent(agent)
    return agent
