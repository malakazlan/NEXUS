"""DynamicToolCreator — the self-evolution engine.

Pipeline: ToolSpec + code → sandbox test → persist → register as MCP tool.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from nexus.events.approval import ApprovalGate
from nexus.events.bus import EventBus
from nexus.events.types import EventType, NexusEvent
from nexus.mcp_layer.registry import ToolRegistry
from nexus.mcp_layer.sandbox import Sandbox, SandboxResult

logger = logging.getLogger(__name__)


class ToolSpec(BaseModel):
    """Specification for a dynamically created tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] = Field(default_factory=dict)
    proposed_by: str  # agent_id that requested this tool


class ToolCreationResult(BaseModel):
    """Result of the tool creation pipeline."""

    success: bool
    tool_name: str
    error: str | None = None
    sandbox_result: dict[str, Any] | None = None


class DynamicToolCreator:
    """Creates, tests, persists, and registers new MCP tools at runtime.

    This is the core of NEXUS self-evolution. When an agent proposes a new tool:
    1. Human approval is requested (if enabled)
    2. Code is tested in the sandbox
    3. If tests pass, tool is persisted to disk
    4. Tool is registered in the ToolRegistry, available to all agents
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        tool_registry: ToolRegistry,
        sandbox: Sandbox,
        approval_gate: ApprovalGate,
        tools_dir: Path,
    ) -> None:
        self._bus = event_bus
        self._registry = tool_registry
        self._sandbox = sandbox
        self._approval = approval_gate
        self._tools_dir = tools_dir
        self._tools_dir.mkdir(parents=True, exist_ok=True)

    async def create_tool(
        self,
        spec: ToolSpec,
        tool_code: str,
        test_code: str,
    ) -> ToolCreationResult:
        """Full pipeline: approve → test → persist → register.

        Args:
            spec: Tool specification (name, description, schema).
            tool_code: Python source for the tool function.
                       Must define an async function matching spec.name.
            test_code: Pytest test file source. Tests import from `tool`.

        Returns:
            ToolCreationResult with success status and details.
        """
        # 1. Emit proposal event
        await self._bus.emit(
            NexusEvent(
                type=EventType.TOOL_PROPOSED,
                source=spec.proposed_by,
                data={"tool_name": spec.name, "description": spec.description},
            )
        )

        # 2. Request human approval
        approved = await self._approval.request(
            action="tool.create",
            description=f"Create tool '{spec.name}': {spec.description}",
            details={"spec": spec.model_dump(), "code_length": len(tool_code)},
            source=spec.proposed_by,
        )

        if not approved:
            logger.info("Tool creation denied: %s", spec.name)
            return ToolCreationResult(
                success=False,
                tool_name=spec.name,
                error="Human approval denied",
            )

        # 3. Test in sandbox
        await self._bus.emit(
            NexusEvent(
                type=EventType.TOOL_TESTING,
                source=spec.proposed_by,
                data={"tool_name": spec.name},
            )
        )

        sandbox_result = await self._sandbox.run_tests(tool_code, test_code)

        if not sandbox_result.success:
            logger.warning(
                "Tool %s failed sandbox tests: %d passed, %d failed",
                spec.name,
                sandbox_result.tests_passed,
                sandbox_result.tests_failed,
            )
            await self._bus.emit(
                NexusEvent(
                    type=EventType.TOOL_FAILED,
                    source=spec.proposed_by,
                    data={
                        "tool_name": spec.name,
                        "tests_passed": sandbox_result.tests_passed,
                        "tests_failed": sandbox_result.tests_failed,
                        "stderr": sandbox_result.stderr[:500],
                    },
                )
            )
            return ToolCreationResult(
                success=False,
                tool_name=spec.name,
                error=f"Sandbox tests failed: {sandbox_result.tests_failed} failures",
                sandbox_result={
                    "stdout": sandbox_result.stdout,
                    "stderr": sandbox_result.stderr,
                    "tests_passed": sandbox_result.tests_passed,
                    "tests_failed": sandbox_result.tests_failed,
                },
            )

        # 4. Persist to disk
        self._persist_tool(spec, tool_code, test_code)

        # 5. Register in the tool registry
        func = self._load_tool_function(spec.name, tool_code)
        self._registry.register(
            name=spec.name,
            description=spec.description,
            input_schema=spec.input_schema,
            func=func,
            output_schema=spec.output_schema,
            is_builtin=False,
            created_by=spec.proposed_by,
        )

        await self._bus.emit(
            NexusEvent(
                type=EventType.TOOL_CREATED,
                source=spec.proposed_by,
                data={
                    "tool_name": spec.name,
                    "tests_passed": sandbox_result.tests_passed,
                },
            )
        )

        logger.info(
            "Tool created: %s (by %s, %d tests passed)",
            spec.name,
            spec.proposed_by,
            sandbox_result.tests_passed,
        )
        return ToolCreationResult(success=True, tool_name=spec.name)

    async def load_persisted_tools(
        self, registry: ToolRegistry | None = None,
    ) -> int:
        """Load all persisted tools from disk into the registry.

        Called at kernel boot to restore tools from previous sessions.
        Returns the number of tools loaded.
        """
        target = registry or self._registry
        loaded = 0

        if not self._tools_dir.exists():
            return 0

        for tool_dir in self._tools_dir.iterdir():
            if not tool_dir.is_dir():
                continue

            manifest_path = tool_dir / "manifest.json"
            tool_path = tool_dir / "tool.py"

            if not manifest_path.exists() or not tool_path.exists():
                continue

            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                tool_code = tool_path.read_text(encoding="utf-8")

                func = self._load_tool_function(manifest["name"], tool_code)
                target.register(
                    name=manifest["name"],
                    description=manifest["description"],
                    input_schema=manifest["input_schema"],
                    func=func,
                    output_schema=manifest.get("output_schema", {}),
                    is_builtin=False,
                    created_by=manifest.get("created_by"),
                )
                loaded += 1
                logger.info("Loaded persisted tool: %s", manifest["name"])
            except Exception as e:
                logger.error("Failed to load tool from %s: %s", tool_dir, e)

        return loaded

    def _persist_tool(
        self, spec: ToolSpec, tool_code: str, test_code: str,
    ) -> None:
        """Save tool code, tests, and manifest to disk."""
        tool_dir = self._tools_dir / spec.name
        tool_dir.mkdir(parents=True, exist_ok=True)

        (tool_dir / "tool.py").write_text(tool_code, encoding="utf-8")
        (tool_dir / "tests.py").write_text(test_code, encoding="utf-8")

        manifest = {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_schema,
            "output_schema": spec.output_schema,
            "proposed_by": spec.proposed_by,
            "created_by": spec.proposed_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (tool_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8",
        )
        logger.info("Persisted tool to %s", tool_dir)

    @staticmethod
    def _load_tool_function(name: str, source_code: str):
        """Dynamically load a tool function from source code string.

        Creates a module from the source and extracts the named function.
        """
        module_name = f"nexus_dynamic_tool_{name}"

        # Remove module if it was previously loaded (hot reload)
        if module_name in sys.modules:
            del sys.modules[module_name]

        spec = importlib.util.spec_from_loader(module_name, loader=None)
        module = importlib.util.module_from_spec(spec)
        exec(compile(source_code, f"<tool:{name}>", "exec"), module.__dict__)
        sys.modules[module_name] = module

        func = getattr(module, name, None)
        if func is None:
            raise ValueError(
                f"Tool source must define a function named '{name}', "
                f"but found: {[k for k in module.__dict__ if not k.startswith('_')]}"
            )
        return func
