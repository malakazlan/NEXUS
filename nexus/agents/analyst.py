"""Analyst agent — data analysis, reasoning, visualization."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nexus.agents.base import AgentStatus, BaseAgent, TaskResult
from nexus.kernel.scheduler import Task

if TYPE_CHECKING:
    from nexus.kernel.kernel import Kernel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a NEXUS Analyst Agent — an expert in data analysis and reasoning.

Your capabilities:
- Analyze structured and unstructured data
- Execute Python code for data analysis (pandas, statistics) via code_executor
- Read data files from the workspace
- Generate insights, summaries, and visualizations

Guidelines:
- Use pandas/numpy for data analysis when appropriate
- Support claims with data, not assumptions
- Visualize data when it adds clarity
- Structure outputs with clear sections: Summary, Analysis, Recommendations
"""


class AnalystAgent(BaseAgent):
    """Agent specialized in data analysis and reasoning."""

    def __init__(self, kernel: Kernel) -> None:
        super().__init__(
            kernel=kernel,
            agent_type="analyst",
            capabilities=["data_analysis", "visualization", "statistical_reasoning"],
            tools=["code_executor", "file_read", "file_list"],
            system_prompt=SYSTEM_PROMPT,
        )

    async def run(self, task: Task) -> TaskResult:
        self.status = AgentStatus.RUNNING
        logger.info("Analyst %s working on: %s", self.id, task.description)

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
            logger.error("Analyst %s failed: %s", self.id, e, exc_info=True)
            self.status = AgentStatus.FAILED
            return TaskResult(success=False, error=str(e))
