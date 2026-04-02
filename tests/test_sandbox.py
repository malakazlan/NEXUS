"""Tests for the tool creation sandbox."""

import pytest
from nexus.mcp_layer.sandbox import Sandbox, SandboxResult


@pytest.fixture
def sandbox(tmp_path):
    return Sandbox(workspace=tmp_path, timeout=10, memory_limit_mb=128)


@pytest.mark.asyncio
async def test_passing_code(sandbox):
    """Code that exits 0 returns success."""
    code = 'print("hello world")'
    result = await sandbox.run(code)

    assert isinstance(result, SandboxResult)
    assert result.success is True
    assert "hello world" in result.stdout
    assert result.return_code == 0


@pytest.mark.asyncio
async def test_failing_code(sandbox):
    """Code that raises returns failure with stderr."""
    code = 'raise ValueError("broken")'
    result = await sandbox.run(code)

    assert result.success is False
    assert "broken" in result.stderr
    assert result.return_code != 0


@pytest.mark.asyncio
async def test_timeout(sandbox):
    """Code exceeding timeout is killed."""
    code = "import time; time.sleep(60)"
    sandbox_short = Sandbox(workspace=sandbox._workspace, timeout=2)
    result = await sandbox_short.run(code)

    assert result.success is False
    assert "timed out" in result.stderr.lower()


@pytest.mark.asyncio
async def test_run_tests_all_pass(sandbox):
    """run_tests returns success when all tests pass."""
    tool_code = '''
def add(a: int, b: int) -> int:
    return a + b
'''
    test_code = '''
from tool import add

def test_add_positive():
    assert add(2, 3) == 5

def test_add_negative():
    assert add(-1, -1) == -2

def test_add_zero():
    assert add(0, 0) == 0
'''
    result = await sandbox.run_tests(tool_code, test_code)

    assert result.success is True
    assert result.tests_passed >= 3
    assert result.tests_failed == 0


@pytest.mark.asyncio
async def test_run_tests_some_fail(sandbox):
    """run_tests reports failures correctly."""
    tool_code = '''
def add(a: int, b: int) -> int:
    return a + b + 1  # bug!
'''
    test_code = '''
from tool import add

def test_add():
    assert add(2, 3) == 5  # will fail: returns 6
'''
    result = await sandbox.run_tests(tool_code, test_code)

    assert result.success is False
    assert result.tests_failed >= 1
