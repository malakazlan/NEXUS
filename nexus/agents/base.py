"""BaseAgent — abstract base for all NEXUS agents."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel, Field

from nexus.memory.short_term import ShortTermMemory

if TYPE_CHECKING:
    from nexus.kernel.kernel import Kernel

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    INIT = "init"
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class TaskResult(BaseModel):
    """Result returned from an agent's run()."""
    success: bool
    output: Any = None
    error: str | None = None
    tokens_used: int = 0


class BaseAgent(ABC):
    """Abstract base for all NEXUS agents.

    Lifecycle: INIT → IDLE → RUNNING → COMPLETED / FAILED / TERMINATED
    """

    def __init__(
        self,
        *,
        kernel: Kernel,
        agent_type: str,
        capabilities: list[str],
        tools: list[str] | None = None,
        model: str | None = None,
        system_prompt: str = "",
        token_budget: int = 100_000,
    ) -> None:
        self.id: str = f"{agent_type}-{uuid4().hex[:8]}"
        self.type: str = agent_type
        self.capabilities: list[str] = capabilities
        self.tool_names: list[str] = tools or []
        self.model: str = model or kernel.config.default_model
        self.system_prompt: str = system_prompt
        self.token_budget: int = token_budget
        self.status: AgentStatus = AgentStatus.INIT

        # References to kernel subsystems
        self._kernel = kernel
        self._memory = ShortTermMemory()

    # ── Core loop ────────────────────────────────────────────────────

    @abstractmethod
    async def run(self, task: Any) -> TaskResult:
        """Execute a task.  Must be implemented by subclasses."""
        ...

    # ── LLM calls ────────────────────────────────────────────────────

    async def llm_call(
        self,
        messages: list[dict[str, Any]] | None = None,
        *,
        use_tools: bool = True,
    ) -> dict[str, Any]:
        """Make an LLM call via litellm, optionally with tool definitions."""
        import litellm

        if not self._kernel.resource_mgr.check_budget(self.id):
            raise RuntimeError(f"Agent {self.id} exceeded token budget")

        msgs = messages or self._memory.get_messages()

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": msgs,
        }

        # Attach tools if requested and agent has tool access
        if use_tools and self.tool_names:
            tool_defs = self._kernel.tool_registry.list_for_llm(self.tool_names)
            if tool_defs:
                kwargs["tools"] = tool_defs

        response = await litellm.acompletion(**kwargs)

        # Track token usage
        usage = response.usage  # type: ignore[union-attr]
        if usage:
            self._kernel.resource_mgr.record_usage(
                self.id,
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
            )

        return response  # type: ignore[return-value]

    # ── Tool execution ───────────────────────────────────────────────

    async def use_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Execute a registered MCP tool."""
        logger.info("Agent %s calling tool: %s(%s)", self.id, tool_name, json.dumps(arguments)[:200])
        result = await self._kernel.tool_registry.call(tool_name, **arguments)
        return result

    async def process_tool_calls(self, response: Any) -> str | None:
        """Process tool calls from an LLM response, execute them, and return final content.

        Handles the full tool-call loop: call tools → feed results back → get final response.
        """
        message = response.choices[0].message  # type: ignore[union-attr]

        if not getattr(message, "tool_calls", None):
            return message.content

        # Execute each tool call
        self._memory.add("assistant", message.content or "", tool_calls=[
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in message.tool_calls
        ])

        for tool_call in message.tool_calls:
            fn_name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments)
                result = await self.use_tool(fn_name, args)
                result_str = json.dumps(result) if not isinstance(result, str) else result
            except Exception as e:
                logger.error("Tool %s failed: %s", fn_name, e)
                result_str = json.dumps({"error": str(e)})

            self._memory.add("tool", result_str, tool_call_id=tool_call.id, name=fn_name)

        # Get the LLM's response after tool results
        followup = await self.llm_call()
        followup_msg = followup.choices[0].message  # type: ignore[union-attr]

        # Recursive: LLM might call more tools
        if getattr(followup_msg, "tool_calls", None):
            return await self.process_tool_calls(followup)

        content = followup_msg.content
        if content:
            self._memory.add("assistant", content)
        return content

    # ── Helpers ──────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        usage = self._kernel.resource_mgr.get_usage(self.id)
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status.value,
            "capabilities": self.capabilities,
            "tools": self.tool_names,
            "model": self.model,
            "tokens_used": usage.total_tokens if usage else 0,
            "token_budget": self.token_budget,
        }
