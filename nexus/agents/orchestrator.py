"""Orchestrator agent — decomposes tasks, spawns sub-agents, aggregates results."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from nexus.agents.base import AgentStatus, BaseAgent, TaskResult
from nexus.kernel.scheduler import Task, TaskStatus

if TYPE_CHECKING:
    from nexus.kernel.kernel import Kernel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the NEXUS Orchestrator — a task planning and delegation agent.

Your job:
1. Analyze the user's request.
2. Decide whether you can answer directly or need to delegate to specialist agents.
3. If delegation is needed, create a plan and specify which agent types to use.

Available agent types:
- researcher: Web search, information gathering, summarization
- coder: Code generation, code review, tool creation
- analyst: Data analysis, statistical reasoning, visualization

Available tools for direct use: web_search, web_fetch

When you need to delegate, respond with a JSON plan:
{
  "plan": "Brief description of your approach",
  "steps": [
    {
      "agent_type": "researcher",
      "task": "Specific task description for the agent",
      "tools": ["web_search", "web_fetch"]
    }
  ]
}

If the task is simple enough to handle directly (e.g., using web_search), just answer directly.
Always be concise and actionable.
"""


class OrchestratorAgent(BaseAgent):
    """Top-level agent that decomposes tasks and delegates to specialists."""

    def __init__(self, kernel: Kernel) -> None:
        super().__init__(
            kernel=kernel,
            agent_type="orchestrator",
            capabilities=["planning", "delegation", "synthesis"],
            tools=["web_search", "web_fetch"],
            system_prompt=SYSTEM_PROMPT,
        )

    async def run(self, task: Task) -> TaskResult:
        self.status = AgentStatus.RUNNING
        logger.info("Orchestrator %s handling task: %s", self.id, task.description)

        try:
            # Set up conversation
            self._memory.clear()
            self._memory.add("system", self.system_prompt)
            self._memory.add("user", task.description)

            # Ask the LLM for a plan or direct answer
            response = await self.llm_call()
            message = response.choices[0].message  # type: ignore[union-attr]

            # Handle tool calls (direct execution by orchestrator)
            if getattr(message, "tool_calls", None):
                content = await self.process_tool_calls(response)
                self.status = AgentStatus.COMPLETED
                return TaskResult(success=True, output=content)

            content = message.content or ""
            self._memory.add("assistant", content)

            # Check if the response is a delegation plan
            plan = self._try_parse_plan(content)
            if plan:
                result = await self._execute_plan(plan, task)
                self.status = AgentStatus.COMPLETED
                return result

            # Direct answer
            self.status = AgentStatus.COMPLETED
            return TaskResult(success=True, output=content)

        except Exception as e:
            logger.error("Orchestrator failed: %s", e, exc_info=True)
            self.status = AgentStatus.FAILED
            return TaskResult(success=False, error=str(e))

    async def _execute_plan(self, plan: dict[str, Any], parent_task: Task) -> TaskResult:
        """Execute a multi-step delegation plan."""
        logger.info("Executing plan: %s", plan.get("plan", ""))
        results: list[str] = []

        for i, step in enumerate(plan.get("steps", []), 1):
            agent_type = step.get("agent_type", "researcher")
            step_task = step.get("task", "")
            tools = step.get("tools", [])

            logger.info("Step %d: %s → %s", i, agent_type, step_task)

            # Spawn the specialist agent
            agent = await self._spawn_specialist(agent_type, tools)
            if agent is None:
                results.append(f"Step {i}: Failed to spawn {agent_type}")
                continue

            # Create a subtask
            subtask = Task(
                description=step_task,
                parent_task_id=parent_task.id,
                token_budget=parent_task.token_budget // max(len(plan.get("steps", [])), 1),
            )

            # Run the agent
            result = await agent.run(subtask)
            if result.success:
                results.append(f"## Step {i}: {step_task}\n\n{result.output}")
            else:
                results.append(f"## Step {i}: {step_task}\n\nFailed: {result.error}")

            # Clean up the agent
            await self._kernel.kill_agent(agent.id)

        # Synthesize results
        synthesis = await self._synthesize(results, parent_task.description)
        return TaskResult(success=True, output=synthesis)

    async def _spawn_specialist(self, agent_type: str, tools: list[str]) -> BaseAgent | None:
        """Spawn a specialist agent by type."""
        try:
            if agent_type == "researcher":
                from nexus.agents.researcher import ResearcherAgent
                agent = ResearcherAgent(kernel=self._kernel, tools=tools or None)
            elif agent_type == "coder":
                from nexus.agents.coder import CoderAgent
                agent = CoderAgent(kernel=self._kernel)
            elif agent_type == "analyst":
                from nexus.agents.analyst import AnalystAgent
                agent = AnalystAgent(kernel=self._kernel)
            else:
                logger.warning("Unknown agent type: %s, defaulting to researcher", agent_type)
                from nexus.agents.researcher import ResearcherAgent
                agent = ResearcherAgent(kernel=self._kernel, tools=tools or None)

            await self._kernel.spawn_agent(agent)
            return agent
        except Exception as e:
            logger.error("Failed to spawn %s: %s", agent_type, e)
            return None

    async def _synthesize(self, results: list[str], original_task: str) -> str:
        """Ask the LLM to synthesize all sub-agent results."""
        combined = "\n\n---\n\n".join(results)
        self._memory.add(
            "user",
            f"Here are the results from the specialist agents:\n\n{combined}\n\n"
            f"Please synthesize these into a coherent final answer for the original task: {original_task}",
        )
        response = await self.llm_call(use_tools=False)
        msg = response.choices[0].message  # type: ignore[union-attr]
        return msg.content or combined

    def _try_parse_plan(self, content: str) -> dict[str, Any] | None:
        """Try to extract a JSON plan from the LLM response."""
        # Look for JSON in the response
        try:
            # Try the full content first
            data = json.loads(content)
            if "steps" in data:
                return data
        except (json.JSONDecodeError, TypeError):
            pass

        # Try to find JSON block in markdown
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                if "steps" in data:
                    return data
            except (json.JSONDecodeError, TypeError):
                pass

        return None
