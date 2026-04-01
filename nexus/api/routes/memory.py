"""Memory routes — read/write shared state."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/memory", tags=["Memory"])

_kernel = None


def init(kernel: Any) -> None:
    global _kernel
    _kernel = kernel


class MemoryWrite(BaseModel):
    key: str
    value: Any


@router.get("/{key}")
async def get_memory(key: str) -> dict:
    value = _kernel.shared_memory.get(key)
    if value is None:
        raise HTTPException(404, f"Key not found: {key}")
    return {"key": key, "value": value}


@router.post("")
async def set_memory(body: MemoryWrite) -> dict:
    await _kernel.shared_memory.set(body.key, body.value, source="api")
    return {"key": body.key, "status": "written"}


@router.get("")
async def list_keys() -> dict:
    return {"keys": _kernel.shared_memory.keys()}
