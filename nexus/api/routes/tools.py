"""Tool routes — list registered MCP tools and create dynamic tools."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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


class ToolCreateRequest(BaseModel):
    name: str
    description: str
    input_schema: dict
    tool_code: str
    test_code: str


@router.post("", status_code=201)
async def create_tool(req: ToolCreateRequest):
    """Create a dynamic tool via the API (for testing/manual use)."""
    if _kernel is None or _kernel.tool_creator is None:
        raise HTTPException(status_code=503, detail="Tool creator not available")

    from nexus.mcp_layer.creator import ToolSpec

    spec = ToolSpec(
        name=req.name,
        description=req.description,
        input_schema=req.input_schema,
        proposed_by="api",
    )
    result = await _kernel.tool_creator.create_tool(spec, req.tool_code, req.test_code)

    if result.success:
        return {"status": "created", "tool_name": result.tool_name}
    raise HTTPException(status_code=400, detail=result.error or "Tool creation failed")
