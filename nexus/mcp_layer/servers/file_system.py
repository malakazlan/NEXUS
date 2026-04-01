"""Built-in MCP server: file_system — sandboxed file operations."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from nexus.config import get_config
from nexus.mcp_layer.registry import ToolRegistry

logger = logging.getLogger(__name__)

INPUT_SCHEMA_READ: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Relative path within workspace."},
    },
    "required": ["path"],
}

INPUT_SCHEMA_WRITE: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Relative path within workspace."},
        "content": {"type": "string", "description": "Content to write."},
    },
    "required": ["path", "content"],
}

INPUT_SCHEMA_LIST: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Relative directory path within workspace.", "default": "."},
    },
}


def _resolve(rel_path: str) -> Path:
    """Resolve a relative path within the sandbox workspace."""
    workspace = get_config().workspace_dir.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    resolved = (workspace / rel_path).resolve()
    # Prevent path traversal
    if not str(resolved).startswith(str(workspace)):
        raise PermissionError(f"Path escapes workspace: {rel_path}")
    return resolved


async def file_read(path: str) -> dict[str, Any]:
    """Read a file from the workspace."""
    fp = _resolve(path)
    if not fp.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    content = fp.read_text(encoding="utf-8")
    return {"path": path, "content": content, "size": len(content)}


async def file_write(path: str, content: str) -> dict[str, Any]:
    """Write content to a file in the workspace."""
    fp = _resolve(path)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content, encoding="utf-8")
    return {"path": path, "size": len(content), "status": "written"}


async def file_list(path: str = ".") -> dict[str, Any]:
    """List files and directories in a workspace path."""
    dp = _resolve(path)
    if not dp.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")
    entries = []
    for child in sorted(dp.iterdir()):
        entries.append({
            "name": child.name,
            "type": "directory" if child.is_dir() else "file",
            "size": child.stat().st_size if child.is_file() else None,
        })
    return {"path": path, "entries": entries}


def register(registry: ToolRegistry) -> None:
    registry.register(
        name="file_read",
        description="Read a file from the sandboxed workspace directory.",
        input_schema=INPUT_SCHEMA_READ,
        func=file_read,
    )
    registry.register(
        name="file_write",
        description="Write content to a file in the sandboxed workspace directory.",
        input_schema=INPUT_SCHEMA_WRITE,
        func=file_write,
    )
    registry.register(
        name="file_list",
        description="List files and directories in the sandboxed workspace.",
        input_schema=INPUT_SCHEMA_LIST,
        func=file_list,
    )
