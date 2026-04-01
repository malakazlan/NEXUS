"""Built-in MCP server: code_executor — run Python code in isolated subprocess."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Any

from nexus.config import get_config
from nexus.mcp_layer.registry import ToolRegistry

logger = logging.getLogger(__name__)

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "code": {
            "type": "string",
            "description": "Python code to execute.",
        },
        "timeout": {
            "type": "integer",
            "description": "Max execution time in seconds (default 30).",
            "default": 30,
        },
    },
    "required": ["code"],
}


async def code_executor(code: str, timeout: int = 30) -> dict[str, Any]:
    """Execute Python code in a subprocess with timeout."""
    cfg = get_config()
    timeout = min(timeout, cfg.tool_creation_timeout)

    # Write code to a temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir=None
    ) as f:
        f.write(code)
        script_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "python",
            script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cfg.workspace_dir.resolve()),
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout}s",
                "return_code": -1,
            }

        return {
            "success": proc.returncode == 0,
            "stdout": stdout.decode(errors="replace")[:10000],
            "stderr": stderr.decode(errors="replace")[:5000],
            "return_code": proc.returncode,
        }
    finally:
        Path(script_path).unlink(missing_ok=True)


def register(registry: ToolRegistry) -> None:
    registry.register(
        name="code_executor",
        description="Execute Python code in an isolated subprocess with a timeout. Returns stdout, stderr, and return code.",
        input_schema=INPUT_SCHEMA,
        func=code_executor,
    )
