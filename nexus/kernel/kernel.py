"""NEXUS Kernel — the core that manages agents, tasks, tools, and memory."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from nexus.config import NexusConfig, get_config
from nexus.events.bus import EventBus
from nexus.events.types import EventType, NexusEvent
from nexus.kernel.registry import AgentRegistry
from nexus.kernel.resource import ResourceManager
from nexus.kernel.scheduler import Task, TaskScheduler, TaskStatus
from nexus.mcp_layer.registry import ToolRegistry
from nexus.agents.messaging import MessageRouter
from nexus.events.approval import ApprovalGate
from nexus.memory.long_term import LongTermMemory
from nexus.memory.shared import SharedMemory
from nexus.mcp_layer.creator import DynamicToolCreator
from nexus.mcp_layer.sandbox import Sandbox

if TYPE_CHECKING:
    from nexus.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class Kernel:
    """The NEXUS kernel: boots the system, manages agents, routes tasks."""

    def __init__(self, config: NexusConfig | None = None) -> None:
        self.config = config or get_config()
        self.event_bus = EventBus()
        self.agent_registry = AgentRegistry()
        self.scheduler = TaskScheduler()
        self.resource_mgr = ResourceManager()
        self.tool_registry = ToolRegistry()
        self.shared_memory = SharedMemory(self.event_bus)
        self.message_router = MessageRouter(self.event_bus)
        self.long_term_memory: LongTermMemory | None = None
        self.approval_gate: ApprovalGate | None = None
        self.tool_creator: DynamicToolCreator | None = None
        self._booted = False

    # ── Lifecycle ────────────────────────────────────────────────────

    async def boot(self) -> None:
        """Initialize the kernel and register built-in tools."""
        if self._booted:
            return

        logger.info("NEXUS Kernel booting...")

        # Register built-in MCP servers
        self._register_builtin_tools()

        # Ensure workspace exists
        self.config.workspace_dir.mkdir(parents=True, exist_ok=True)

        # Initialize long-term memory (ChromaDB)
        persist_dir = str(self.config.workspace_dir / "chromadb")
        self.long_term_memory = LongTermMemory(persist_dir=persist_dir)

        # Initialize approval gate
        auto_approve = not self.config.require_approval_for_tools
        self.approval_gate = ApprovalGate(self.event_bus, auto_approve=auto_approve)

        # Initialize tool creator (self-evolution engine)
        sandbox = Sandbox(
            workspace=self.config.workspace_dir / "sandbox",
            timeout=self.config.tool_creation_timeout,
        )
        self.tool_creator = DynamicToolCreator(
            event_bus=self.event_bus,
            tool_registry=self.tool_registry,
            sandbox=sandbox,
            approval_gate=self.approval_gate,
            tools_dir=self.config.tools_dir,
        )

        # Load persisted tools from previous sessions
        loaded = await self.tool_creator.load_persisted_tools()
        if loaded:
            logger.info("Loaded %d persisted dynamic tools", loaded)

        self._booted = True
        await self.event_bus.emit(
            NexusEvent(type=EventType.KERNEL_BOOT, source="kernel", data={"version": "0.1.0"})
        )
        logger.info("NEXUS Kernel booted.  %d tools registered.", len(self.tool_registry.list_tools()))

    async def shutdown(self) -> None:
        """Graceful shutdown — terminate all agents, clear state."""
        logger.info("NEXUS Kernel shutting down...")

        # Terminate running agents
        for agent in list(self.agent_registry.list_all()):
            await self.kill_agent(agent.id)

        await self.event_bus.emit(
            NexusEvent(type=EventType.KERNEL_SHUTDOWN, source="kernel")
        )
        self.event_bus.clear()
        self._booted = False
        logger.info("NEXUS Kernel stopped.")

    # ── Agent management ─────────────────────────────────────────────

    async def spawn_agent(self, agent: BaseAgent) -> BaseAgent:
        """Register and initialize an agent."""
        if self.agent_registry.count() >= self.config.max_agents:
            raise RuntimeError(
                f"Max agents ({self.config.max_agents}) reached. "
                "Kill an existing agent or raise the limit."
            )

        self.agent_registry.register(agent)
        self.resource_mgr.init_agent(agent.id, budget=agent.token_budget)

        await self.event_bus.emit(
            NexusEvent(
                type=EventType.AGENT_SPAWNED,
                source="kernel",
                data={"agent_id": agent.id, "agent_type": agent.type, "capabilities": agent.capabilities},
            )
        )
        logger.info("Agent spawned: %s (%s)", agent.id, agent.type)
        return agent

    async def kill_agent(self, agent_id: str) -> bool:
        """Terminate an agent."""
        agent = self.agent_registry.unregister(agent_id)
        if agent is None:
            return False

        from nexus.agents.base import AgentStatus
        agent.status = AgentStatus.TERMINATED
        self.resource_mgr.remove_agent(agent_id)

        await self.event_bus.emit(
            NexusEvent(
                type=EventType.AGENT_TERMINATED,
                source="kernel",
                data={"agent_id": agent_id},
            )
        )
        return True

    # ── Task management ──────────────────────────────────────────────

    async def submit_task(self, description: str, *, priority: int = 5, parent_task_id: str | None = None) -> Task:
        """Create and enqueue a new task.  Returns the Task for tracking."""
        task = Task(
            description=description,
            priority=priority,
            parent_task_id=parent_task_id,
            token_budget=self.config.token_budget_per_task,
        )
        await self.scheduler.submit(task)

        await self.event_bus.emit(
            NexusEvent(
                type=EventType.TASK_CREATED,
                source="kernel",
                data={"task_id": task.id, "description": description, "priority": priority},
            )
        )
        return task

    async def run_task(self, description: str, *, priority: int = 5) -> Task:
        """Submit a task and execute it through the orchestrator end-to-end."""
        task = await self.submit_task(description, priority=priority)
        # Import here to avoid circular imports
        from nexus.agents.orchestrator import OrchestratorAgent

        # Find or spawn an orchestrator
        orchestrators = self.agent_registry.find_by_type("orchestrator")
        if orchestrators:
            orchestrator = orchestrators[0]
        else:
            orchestrator = OrchestratorAgent(kernel=self)
            await self.spawn_agent(orchestrator)

        # Assign and run
        self.scheduler.update_task(task.id, status=TaskStatus.ASSIGNED, assigned_to=orchestrator.id)
        await self.event_bus.emit(
            NexusEvent(
                type=EventType.TASK_ASSIGNED,
                source="kernel",
                data={"task_id": task.id, "agent_id": orchestrator.id},
            )
        )

        result = await orchestrator.run(task)

        # Update task with result
        if result.success:
            self.scheduler.update_task(task.id, status=TaskStatus.COMPLETED, result=result.output)
            await self.event_bus.emit(
                NexusEvent(type=EventType.TASK_COMPLETED, source="kernel", data={"task_id": task.id})
            )
        else:
            self.scheduler.update_task(task.id, status=TaskStatus.FAILED, error=result.error)
            await self.event_bus.emit(
                NexusEvent(type=EventType.TASK_FAILED, source="kernel", data={"task_id": task.id, "error": result.error})
            )

        return self.scheduler.get_task(task.id)  # type: ignore[return-value]

    # ── Internal ─────────────────────────────────────────────────────

    def _register_builtin_tools(self) -> None:
        """Register all built-in MCP servers."""
        from nexus.mcp_layer.servers import web_search, web_fetch, file_system, code_executor

        web_search.register(self.tool_registry)
        web_fetch.register(self.tool_registry)
        file_system.register(self.tool_registry)
        code_executor.register(self.tool_registry)
