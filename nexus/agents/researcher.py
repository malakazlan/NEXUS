"""Researcher agent — web search, information gathering, summarization."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nexus.agents.base import AgentStatus, BaseAgent, TaskResult
from nexus.kernel.scheduler import Task

if TYPE_CHECKING:
    from nexus.kernel.kernel import Kernel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a NEXUS Research Agent — an expert at finding and synthesizing information.

Your capabilities:
- Search the web for relevant information using the web_search tool
- Fetch and read full web pages using the web_fetch tool
- Summarize and synthesize findings into clear, actionable reports

Guidelines:
- Always search first, then read promising pages for detail
- Cite sources with URLs
- Be thorough but concise
- If the search results are insufficient, try different queries
- Structure your response with clear headings and bullet points
"""


class ResearcherAgent(BaseAgent):
    """Agent specialized in web research and information synthesis."""

    def __init__(self, kernel: Kernel, tools: list[str] | None = None) -> None:
        super().__init__(
            kernel=kernel,
            agent_type="researcher",
            capabilities=["research", "summarization", "fact_checking"],
            tools=tools or ["web_search", "web_fetch"],
            system_prompt=SYSTEM_PROMPT,
        )

    async def run(self, task: Task) -> TaskResult:
        self.status = AgentStatus.RUNNING
        logger.info("Researcher %s working on: %s", self.id, task.description)

        try:
            self._memory.clear()
            self._memory.add("system", self.system_prompt)
            self._memory.add("user", task.description)

            # Let the LLM decide which tools to call
            response = await self.llm_call()
            content = await self.process_tool_calls(response)

            if content is None:
                content = response.choices[0].message.content or "No results found."  # type: ignore[union-attr]

            # Store findings in shared memory
            await self._kernel.shared_memory.set(
                f"research:{task.id}",
                {"task": task.description, "findings": content},
                source=self.id,
            )

            self.status = AgentStatus.COMPLETED
            return TaskResult(success=True, output=content)

        except Exception as e:
            logger.error("Researcher %s failed: %s", self.id, e, exc_info=True)
            self.status = AgentStatus.FAILED
            return TaskResult(success=False, error=str(e))
