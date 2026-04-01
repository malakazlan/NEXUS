"""Built-in MCP server: web_fetch — fetch and extract content from URLs."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from nexus.mcp_layer.registry import ToolRegistry

logger = logging.getLogger(__name__)

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "The URL to fetch content from.",
        },
        "max_length": {
            "type": "integer",
            "description": "Maximum characters to return (default 5000).",
            "default": 5000,
        },
    },
    "required": ["url"],
}


async def web_fetch(url: str, max_length: int = 5000) -> dict[str, Any]:
    """Fetch a URL and return its text content (stripped of HTML)."""
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "NEXUS-Agent/0.1"})
        resp.raise_for_status()
        text = resp.text

    # Naive HTML stripping — good enough for v1
    import re
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_length:
        text = text[:max_length] + "..."

    return {"url": url, "content": text, "length": len(text)}


def register(registry: ToolRegistry) -> None:
    registry.register(
        name="web_fetch",
        description="Fetch content from a URL and return the extracted text.",
        input_schema=INPUT_SCHEMA,
        func=web_fetch,
    )
