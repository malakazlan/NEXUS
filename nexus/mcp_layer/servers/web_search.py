"""Built-in MCP server: web_search via Tavily API."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from nexus.mcp_layer.registry import ToolRegistry

logger = logging.getLogger(__name__)

TAVILY_ENDPOINT = "https://api.tavily.com/search"

INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query.",
        },
        "max_results": {
            "type": "integer",
            "description": "Maximum number of results (default 5).",
            "default": 5,
        },
    },
    "required": ["query"],
}


async def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web using Tavily API and return results."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key or api_key.startswith("tvly-..."):
        # Fallback: return a mock so the system works without a key
        logger.warning("TAVILY_API_KEY not set — returning mock search results")
        return {
            "query": query,
            "results": [
                {
                    "title": f"Mock result for: {query}",
                    "url": "https://example.com",
                    "content": f"This is a placeholder result. Set TAVILY_API_KEY for real search results. Query was: {query}",
                }
            ],
        }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            TAVILY_ENDPOINT,
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": True,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "query": query,
        "answer": data.get("answer", ""),
        "results": [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
            }
            for r in data.get("results", [])
        ],
    }


def register(registry: ToolRegistry) -> None:
    """Register web_search tool in the given registry."""
    registry.register(
        name="web_search",
        description="Search the web for information. Returns relevant web pages with titles, URLs, and content snippets.",
        input_schema=INPUT_SCHEMA,
        func=web_search,
    )
