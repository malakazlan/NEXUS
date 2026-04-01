"""MCP Tool registry — tracks all available tools (built-in and dynamic)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Type alias for a tool's execute function
ToolFunction = Callable[..., Coroutine[Any, Any, Any]]


class RegisteredTool(BaseModel):
    """Metadata for a registered MCP tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] = Field(default_factory=dict)
    is_builtin: bool = True
    created_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    usage_count: int = 0

    model_config = {"arbitrary_types_allowed": True}


class ToolRegistry:
    """Central registry of all MCP tools available to agents.

    Built-in tools are registered as direct async functions (in-process).
    Dynamic tools (Phase 3) will reference subprocess MCP servers.
    """

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}
        self._functions: dict[str, ToolFunction] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        func: ToolFunction,
        *,
        output_schema: dict[str, Any] | None = None,
        is_builtin: bool = True,
        created_by: str | None = None,
    ) -> RegisteredTool:
        """Register a tool with its implementation function."""
        tool = RegisteredTool(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema or {},
            is_builtin=is_builtin,
            created_by=created_by,
        )
        self._tools[name] = tool
        self._functions[name] = func
        logger.info("Registered tool: %s (builtin=%s)", name, is_builtin)
        return tool

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    def get_function(self, name: str) -> ToolFunction | None:
        return self._functions.get(name)

    async def call(self, name: str, **kwargs: Any) -> Any:
        """Execute a tool by name."""
        func = self._functions.get(name)
        if func is None:
            raise KeyError(f"Tool not found: {name}")
        self._tools[name].usage_count += 1
        return await func(**kwargs)

    def list_tools(self) -> list[RegisteredTool]:
        return list(self._tools.values())

    def list_for_llm(self, tool_names: list[str] | None = None) -> list[dict[str, Any]]:
        """Return tool definitions in the format expected by litellm / OpenAI function calling."""
        result = []
        tools = self._tools.values() if tool_names is None else [
            self._tools[n] for n in tool_names if n in self._tools
        ]
        for t in tools:
            result.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            })
        return result

    def has(self, name: str) -> bool:
        return name in self._tools
