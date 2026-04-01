"""Task routes — submit and query tasks."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Kernel reference set at startup
_kernel = None


def init(kernel: Any) -> None:
    global _kernel
    _kernel = kernel


class TaskSubmit(BaseModel):
    description: str
    priority: int = 5


class TaskResponse(BaseModel):
    id: str
    description: str
    priority: int
    status: str
    assigned_to: str | None = None
    result: Any | None = None
    error: str | None = None
    created_at: str
    completed_at: str | None = None


@router.post("", response_model=TaskResponse)
async def submit_task(body: TaskSubmit) -> TaskResponse:
    """Submit a new task and run it through the orchestrator."""
    task = await _kernel.run_task(body.description, priority=body.priority)
    return _task_to_response(task)


@router.post("/async")
async def submit_task_async(body: TaskSubmit) -> dict[str, str]:
    """Submit a task without waiting for completion.  Returns the task ID."""
    task = await _kernel.submit_task(body.description, priority=body.priority)
    # Fire and forget — run in background
    asyncio.create_task(_kernel.run_task(body.description, priority=body.priority))
    return {"task_id": task.id, "status": "submitted"}


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    task = _kernel.scheduler.get_task(task_id)
    if task is None:
        raise HTTPException(404, f"Task not found: {task_id}")
    return _task_to_response(task)


@router.get("", response_model=list[TaskResponse])
async def list_tasks(status: str | None = None) -> list[TaskResponse]:
    from nexus.kernel.scheduler import TaskStatus
    ts = TaskStatus(status) if status else None
    tasks = _kernel.scheduler.list_tasks(status=ts)
    return [_task_to_response(t) for t in tasks]


def _task_to_response(task: Any) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        description=task.description,
        priority=task.priority,
        status=task.status.value,
        assigned_to=task.assigned_to,
        result=task.result,
        error=task.error,
        created_at=task.created_at.isoformat(),
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )
