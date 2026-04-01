"""Agent routes — list, spawn, kill agents."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/agents", tags=["Agents"])

_kernel = None


def init(kernel: Any) -> None:
    global _kernel
    _kernel = kernel


class AgentSpawnRequest(BaseModel):
    type: str = "custom"
    role: str = "You are a helpful assistant."
    capabilities: list[str] = []
    tools: list[str] = []
    model: str | None = None
    token_budget: int = 100_000


@router.get("")
async def list_agents() -> list[dict]:
    agents = _kernel.agent_registry.list_all()
    return [a.to_dict() for a in agents]


@router.post("")
async def spawn_agent(body: AgentSpawnRequest) -> dict:
    from nexus.agents.factory import AgentSpec, create_agent

    spec = AgentSpec(
        type=body.type,
        role=body.role,
        capabilities=body.capabilities,
        tools=body.tools,
        model=body.model,
        token_budget=body.token_budget,
    )
    agent = await create_agent(_kernel, spec)
    return agent.to_dict()


@router.get("/{agent_id}")
async def get_agent(agent_id: str) -> dict:
    agent = _kernel.agent_registry.get(agent_id)
    if agent is None:
        raise HTTPException(404, f"Agent not found: {agent_id}")
    return agent.to_dict()


@router.delete("/{agent_id}")
async def kill_agent(agent_id: str) -> dict:
    ok = await _kernel.kill_agent(agent_id)
    if not ok:
        raise HTTPException(404, f"Agent not found: {agent_id}")
    return {"status": "terminated", "agent_id": agent_id}
