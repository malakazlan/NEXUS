"""Tests for the DynamicToolCreator — agent self-evolution pipeline."""

import pytest
from pathlib import Path
from nexus.events.bus import EventBus
from nexus.events.approval import ApprovalGate
from nexus.mcp_layer.registry import ToolRegistry
from nexus.mcp_layer.sandbox import Sandbox
from nexus.mcp_layer.creator import DynamicToolCreator, ToolSpec


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def tool_registry():
    return ToolRegistry()


@pytest.fixture
def sandbox(tmp_path):
    return Sandbox(workspace=tmp_path, timeout=15)


@pytest.fixture
def approval_gate(event_bus):
    return ApprovalGate(event_bus, auto_approve=True)


@pytest.fixture
def tools_dir(tmp_path):
    d = tmp_path / "tools"
    d.mkdir()
    return d


@pytest.fixture
def creator(event_bus, tool_registry, sandbox, approval_gate, tools_dir):
    return DynamicToolCreator(
        event_bus=event_bus,
        tool_registry=tool_registry,
        sandbox=sandbox,
        approval_gate=approval_gate,
        tools_dir=tools_dir,
    )


@pytest.mark.asyncio
async def test_create_tool_from_code(creator, tool_registry):
    """Create a tool from provided code + tests, register it."""
    spec = ToolSpec(
        name="add_numbers",
        description="Add two numbers together",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["a", "b"],
        },
        proposed_by="coder-test",
    )

    tool_code = '''
async def add_numbers(a: float, b: float) -> dict:
    """Add two numbers."""
    return {"result": a + b}
'''

    test_code = '''
from tool import add_numbers
import asyncio

def test_add_positive():
    result = asyncio.run(add_numbers(2, 3))
    assert result == {"result": 5}

def test_add_negative():
    result = asyncio.run(add_numbers(-1, -1))
    assert result == {"result": -2}

def test_add_float():
    result = asyncio.run(add_numbers(1.5, 2.5))
    assert result == {"result": 4.0}
'''

    result = await creator.create_tool(spec, tool_code, test_code)

    assert result.success is True
    assert tool_registry.has("add_numbers")


@pytest.mark.asyncio
async def test_create_tool_failing_tests(creator, tool_registry):
    """Tool with failing tests is NOT registered."""
    spec = ToolSpec(
        name="broken_tool",
        description="This tool has a bug",
        input_schema={"type": "object", "properties": {"x": {"type": "number"}}},
        proposed_by="coder-test",
    )

    tool_code = '''
async def broken_tool(x: float) -> dict:
    return {"result": x + 1}  # bug: should be x * 2
'''

    test_code = '''
from tool import broken_tool
import asyncio

def test_double():
    result = asyncio.run(broken_tool(5))
    assert result == {"result": 10}  # fails: returns 6
'''

    result = await creator.create_tool(spec, tool_code, test_code)

    assert result.success is False
    assert not tool_registry.has("broken_tool")


@pytest.mark.asyncio
async def test_tool_persisted_to_disk(creator, tools_dir):
    """Created tools are saved to the tools directory."""
    spec = ToolSpec(
        name="multiply",
        description="Multiply two numbers",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
        proposed_by="coder-test",
    )

    tool_code = '''
async def multiply(a: float, b: float) -> dict:
    return {"result": a * b}
'''

    test_code = '''
from tool import multiply
import asyncio

def test_multiply():
    assert asyncio.run(multiply(3, 4)) == {"result": 12}

def test_multiply_zero():
    assert asyncio.run(multiply(5, 0)) == {"result": 0}

def test_multiply_negative():
    assert asyncio.run(multiply(-2, 3)) == {"result": -6}
'''

    await creator.create_tool(spec, tool_code, test_code)

    tool_dir = tools_dir / "multiply"
    assert tool_dir.exists()
    assert (tool_dir / "tool.py").exists()
    assert (tool_dir / "tests.py").exists()
    assert (tool_dir / "manifest.json").exists()


@pytest.mark.asyncio
async def test_load_persisted_tools(creator, tool_registry, tools_dir):
    """Persisted tools can be loaded back into the registry on boot."""
    spec = ToolSpec(
        name="subtract",
        description="Subtract b from a",
        input_schema={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
        proposed_by="coder-test",
    )

    tool_code = '''
async def subtract(a: float, b: float) -> dict:
    return {"result": a - b}
'''

    test_code = '''
from tool import subtract
import asyncio

def test_subtract():
    assert asyncio.run(subtract(10, 3)) == {"result": 7}

def test_subtract_negative():
    assert asyncio.run(subtract(3, 10)) == {"result": -7}

def test_subtract_zero():
    assert asyncio.run(subtract(5, 5)) == {"result": 0}
'''

    await creator.create_tool(spec, tool_code, test_code)

    # Create a fresh registry to simulate reboot
    fresh_registry = ToolRegistry()
    assert not fresh_registry.has("subtract")

    # Load persisted tools
    loaded = await creator.load_persisted_tools(fresh_registry)
    assert loaded == 1
    assert fresh_registry.has("subtract")

    # Verify the loaded tool actually works
    result = await fresh_registry.call("subtract", a=10, b=3)
    assert result == {"result": 7}
