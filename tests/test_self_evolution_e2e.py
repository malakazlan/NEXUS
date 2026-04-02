"""End-to-end test: kernel boots, tool is created, persisted, and loaded on reboot."""

import asyncio
import pytest
from pathlib import Path
from nexus.kernel.kernel import Kernel
from nexus.config import NexusConfig
from nexus.mcp_layer.creator import ToolSpec


@pytest.fixture
def config(tmp_path):
    return NexusConfig(
        workspace_dir=tmp_path / "workspace",
        tools_dir=tmp_path / "tools",
        require_approval_for_tools=False,  # auto-approve for testing
        default_model="gpt-4o-mini",  # cheap model for testing
    )


@pytest.mark.asyncio
async def test_full_tool_lifecycle(config):
    """Boot kernel -> create tool -> verify it works -> shutdown -> reboot -> tool still there."""
    # Boot
    kernel = Kernel(config=config)
    await kernel.boot()

    builtin_count = len(kernel.tool_registry.list_tools())
    assert builtin_count >= 4  # web_search, web_fetch, file_system tools, code_executor

    # Create a dynamic tool
    spec = ToolSpec(
        name="celsius_to_fahrenheit",
        description="Convert Celsius to Fahrenheit",
        input_schema={
            "type": "object",
            "properties": {
                "celsius": {"type": "number", "description": "Temperature in Celsius"},
            },
            "required": ["celsius"],
        },
        proposed_by="test-agent",
    )

    tool_code = '''
async def celsius_to_fahrenheit(celsius: float) -> dict:
    """Convert Celsius to Fahrenheit."""
    return {"fahrenheit": celsius * 9 / 5 + 32}
'''

    test_code = '''
from tool import celsius_to_fahrenheit
import asyncio

def test_boiling():
    result = asyncio.run(celsius_to_fahrenheit(100))
    assert result == {"fahrenheit": 212.0}

def test_freezing():
    result = asyncio.run(celsius_to_fahrenheit(0))
    assert result == {"fahrenheit": 32.0}

def test_body_temp():
    result = asyncio.run(celsius_to_fahrenheit(37))
    assert abs(result["fahrenheit"] - 98.6) < 0.01
'''

    result = await kernel.tool_creator.create_tool(spec, tool_code, test_code)
    assert result.success is True
    assert kernel.tool_registry.has("celsius_to_fahrenheit")

    # Use the tool
    conversion = await kernel.tool_registry.call("celsius_to_fahrenheit", celsius=100)
    assert conversion == {"fahrenheit": 212.0}

    # Verify events were emitted
    history = kernel.event_bus.get_history()
    event_types = [e.type.value for e in history]
    assert "tool.proposed" in event_types
    assert "tool.testing" in event_types
    assert "tool.created" in event_types

    # Shutdown
    await kernel.shutdown()

    # Reboot — tool should be loaded from disk
    kernel2 = Kernel(config=config)
    await kernel2.boot()

    assert kernel2.tool_registry.has("celsius_to_fahrenheit")
    conversion2 = await kernel2.tool_registry.call("celsius_to_fahrenheit", celsius=0)
    assert conversion2 == {"fahrenheit": 32.0}

    total_tools = len(kernel2.tool_registry.list_tools())
    assert total_tools == builtin_count + 1  # built-in + 1 dynamic

    await kernel2.shutdown()
