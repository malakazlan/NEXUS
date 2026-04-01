"""Coder agent — code generation, review, and tool creation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nexus.agents.base import AgentStatus, BaseAgent, TaskResult
from nexus.kernel.scheduler import Task

if TYPE_CHECKING:
    from nexus.kernel.kernel import Kernel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a NEXUS Coder Agent — an expert software engineer.

Your capabilities:
- Generate clean, well-structured Python code
- Execute code to verify correctness using the code_executor tool
- Read and write files in the workspace using file_read and file_write
- Review code and suggest improvements

Guidelines:
- Write production-quality code with proper error handling
- Always test code before declaring it complete
- Use type hints and docstrings
- Keep solutions simple and maintainable
"""


class CoderAgent(BaseAgent):
    """Agent specialized in code generation and execution."""

    def __init__(self, kernel: Kernel) -> None:
        super().__init__(
            kernel=kernel,
            agent_type="coder",
            capabilities=["python", "javascript", "code_review", "tool_creation"],
            tools=["code_executor", "file_read", "file_write", "file_list"],
            system_prompt=SYSTEM_PROMPT,
        )

    async def run(self, task: Task) -> TaskResult:
        self.status = AgentStatus.RUNNING
        logger.info("Coder %s working on: %s", self.id, task.description)

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
            logger.error("Coder %s failed: %s", self.id, e, exc_info=True)
            self.status = AgentStatus.FAILED
            return TaskResult(success=False, error=str(e))
