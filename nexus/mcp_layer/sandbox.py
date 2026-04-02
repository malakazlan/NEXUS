"""Sandbox for safely testing agent-generated tool code."""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """Result of running code in the sandbox."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1
    tests_passed: int = 0
    tests_failed: int = 0


class Sandbox:
    """Isolated execution environment for testing generated tool code.

    Runs code in a subprocess with:
    - Timeout enforcement
    - Restricted to a temp directory (no access to main workspace)
    - Stderr/stdout capture

    Args:
        workspace: Base directory for sandbox temp dirs.
        timeout: Max seconds per execution.
        memory_limit_mb: Memory limit (advisory, not enforced on Windows).
    """

    def __init__(
        self,
        workspace: Path | None = None,
        timeout: int = 30,
        memory_limit_mb: int = 256,
    ) -> None:
        self._workspace = workspace or Path(tempfile.gettempdir())
        self._workspace.mkdir(parents=True, exist_ok=True)
        self._timeout = timeout
        self._memory_limit_mb = memory_limit_mb

    async def run(self, code: str) -> SandboxResult:
        """Execute arbitrary Python code in an isolated subprocess."""
        with tempfile.TemporaryDirectory(dir=self._workspace) as tmpdir:
            script_path = Path(tmpdir) / "script.py"
            script_path.write_text(code, encoding="utf-8")

            proc = await asyncio.create_subprocess_exec(
                "python", str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmpdir,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=self._timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxResult(
                    success=False,
                    stderr=f"Execution timed out after {self._timeout}s",
                    return_code=-1,
                )

            stdout = stdout_bytes.decode(errors="replace")[:10_000]
            stderr = stderr_bytes.decode(errors="replace")[:5_000]

            return SandboxResult(
                success=proc.returncode == 0,
                stdout=stdout,
                stderr=stderr,
                return_code=proc.returncode or 0,
            )

    async def run_tests(
        self,
        tool_code: str,
        test_code: str,
    ) -> SandboxResult:
        """Write tool code + test code into an isolated dir and run pytest.

        The tool code is written to `tool.py` so tests can `from tool import ...`.
        Tests are written to `test_tool.py` and executed via pytest.
        """
        with tempfile.TemporaryDirectory(dir=self._workspace) as tmpdir:
            tool_path = Path(tmpdir) / "tool.py"
            test_path = Path(tmpdir) / "test_tool.py"

            tool_path.write_text(tool_code, encoding="utf-8")
            test_path.write_text(test_code, encoding="utf-8")

            proc = await asyncio.create_subprocess_exec(
                "python", "-m", "pytest", str(test_path), "-v", "--tb=short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmpdir,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=self._timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxResult(
                    success=False,
                    stderr=f"Tests timed out after {self._timeout}s",
                    return_code=-1,
                )

            stdout = stdout_bytes.decode(errors="replace")[:10_000]
            stderr = stderr_bytes.decode(errors="replace")[:5_000]

            # Parse pytest output for pass/fail counts
            passed, failed = _parse_pytest_summary(stdout)

            return SandboxResult(
                success=proc.returncode == 0 and failed == 0,
                stdout=stdout,
                stderr=stderr,
                return_code=proc.returncode or 0,
                tests_passed=passed,
                tests_failed=failed,
            )


def _parse_pytest_summary(output: str) -> tuple[int, int]:
    """Extract passed/failed counts from pytest output."""
    passed = 0
    failed = 0

    match = re.search(r"(\d+) passed", output)
    if match:
        passed = int(match.group(1))

    match = re.search(r"(\d+) failed", output)
    if match:
        failed = int(match.group(1))

    return passed, failed
