"""Event type definitions and the NexusEvent model."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ── Event type string constants ──────────────────────────────────────

class EventType(str, Enum):
    # Kernel
    KERNEL_BOOT = "kernel.boot"
    KERNEL_SHUTDOWN = "kernel.shutdown"

    # Agent lifecycle
    AGENT_SPAWNED = "agent.spawned"
    AGENT_STATUS_CHANGED = "agent.status_changed"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_TERMINATED = "agent.terminated"

    # Agent messaging (IPC)
    AGENT_MESSAGE = "agent.message"

    # Tasks
    TASK_CREATED = "task.created"
    TASK_ASSIGNED = "task.assigned"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # Tools / MCP
    TOOL_PROPOSED = "tool.proposed"
    TOOL_TESTING = "tool.testing"
    TOOL_CREATED = "tool.created"
    TOOL_FAILED = "tool.failed"

    # Memory
    MEMORY_WRITE = "memory.write"
    MEMORY_READ = "memory.read"

    # Approval
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"


# ── Event payload model ─────────────────────────────────────────────

class NexusEvent(BaseModel):
    """A single event emitted within the NEXUS system."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    type: EventType
    source: str  # agent_id or "kernel"
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"frozen": True}
