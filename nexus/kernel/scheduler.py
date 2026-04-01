"""Task scheduler — priority queue with assignment and dependency tracking."""

from __future__ import annotations

import asyncio
import heapq
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """A unit of work submitted to the kernel."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    description: str
    priority: int = 5  # 1 (low) — 10 (high)
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str | None = None
    parent_task_id: str | None = None
    result: Any | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    token_budget: int = 100_000


class TaskScheduler:
    """Priority-based task queue with assignment tracking."""

    def __init__(self) -> None:
        # Min-heap: we negate priority so higher priority = lower heap value
        self._queue: list[tuple[int, float, Task]] = []
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()

    async def submit(self, task: Task) -> Task:
        """Add a task to the queue."""
        async with self._lock:
            self._tasks[task.id] = task
            heapq.heappush(
                self._queue,
                (-task.priority, task.created_at.timestamp(), task),
            )
        logger.info("Task submitted: %s (priority=%d)", task.id, task.priority)
        return task

    async def next_task(self) -> Task | None:
        """Pop the highest-priority pending task."""
        async with self._lock:
            while self._queue:
                _, _, task = heapq.heappop(self._queue)
                # Skip if task was already assigned/completed
                if task.status == TaskStatus.PENDING:
                    return task
        return None

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        *,
        status: TaskStatus | None = None,
        assigned_to: str | None = None,
        result: Any = ...,
        error: str | None = ...,
    ) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        if status is not None:
            task.status = status
        if assigned_to is not None:
            task.assigned_to = assigned_to
        if result is not ...:
            task.result = result
        if error is not ...:
            task.error = error
        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            task.completed_at = datetime.now(timezone.utc)
        return task

    def list_tasks(self, status: TaskStatus | None = None) -> list[Task]:
        tasks = list(self._tasks.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def get_subtasks(self, parent_id: str) -> list[Task]:
        return [t for t in self._tasks.values() if t.parent_task_id == parent_id]
