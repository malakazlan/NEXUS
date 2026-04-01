"""Tool routes — list registered MCP tools."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/tools", tags=["Tools"])

_kernel = None


def init(kernel: Any) -> None:
    global _kernel
    _kernel = kernel


@router.get("")
async def list_tools() -> list[dict]:
    tools = _kernel.tool_registry.list_tools()
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
            "is_builtin": t.is_builtin,
            "created_by": t.created_by,
            "usage_count": t.usage_count,
            "created_at": t.created_at.isoformat(),
        }
        for t in tools
    ]
