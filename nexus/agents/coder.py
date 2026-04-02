"""Coder agent — code generation, review, and tool creation."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING, Any

from nexus.agents.base import AgentStatus, BaseAgent, TaskResult
from nexus.kernel.scheduler import Task

if TYPE_CHECKING:
    from nexus.kernel.kernel import Kernel

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a NEXUS Coder Agent — an expert software engineer.

Your capabilities:
- Generate clean, well-structured Python code
- Execute code to verify correctness using the code_executor tool
- Read and write files in the workspace using file_read and file_write
- Review code and suggest improvements

Guidelines:
- Write production-quality code with proper error handling
- Always test code before declaring it complete
- Use type hints and docstrings
- Keep solutions simple and maintainable
"""

TOOL_GENERATION_PROMPT = """\
Generate a Python tool function and pytest tests for the following specification:

**Tool name:** {name}
**Description:** {description}
**Input schema:** {input_schema}

Requirements:
1. The tool function MUST be async and named exactly `{name}`
2. The function MUST accept keyword arguments matching the input schema properties
3. The function MUST return a dict with the result
4. Write AT LEAST 3 pytest test cases covering normal use, edge cases, and error cases
5. Tests import from `tool` (e.g., `from tool import {name}`)
6. Tests use `asyncio.run()` to call the async function

Respond with EXACTLY this format (no other text):

```tool
<the async function code>
```

```tests
<the pytest test code>
```
"""


class CoderAgent(BaseAgent):
    """Agent specialized in code generation and execution."""

    def __init__(self, kernel: Kernel) -> None:
        super().__init__(
            kernel=kernel,
            agent_type="coder",
            capabilities=["python", "javascript", "code_review", "tool_creation"],
            tools=["code_executor", "file_read", "file_write", "file_list"],
            system_prompt=SYSTEM_PROMPT,
        )

    async def run(self, task: Task) -> TaskResult:
        self.status = AgentStatus.RUNNING
        logger.info("Coder %s working on: %s", self.id, task.description)

        try:
            self._memory.clear()
            self._memory.add("system", self.system_prompt)
            self._memory.add("user", task.description)

            response = await self.llm_call()
            content = await self.process_tool_calls(response)

            if content is None:
                content = response.choices[0].message.content or ""  # type: ignore[union-attr]

            self.status = AgentStatus.COMPLETED
            return TaskResult(success=True, output=content)

        except Exception as e:
            logger.error("Coder %s failed: %s", self.id, e, exc_info=True)
            self.status = AgentStatus.FAILED
            return TaskResult(success=False, error=str(e))

    async def generate_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
    ) -> tuple[str, str] | None:
        """Generate tool code and tests from a specification.

        Returns (tool_code, test_code) tuple, or None if generation fails.
        """
        self.status = AgentStatus.RUNNING
        logger.info("Coder %s generating tool: %s", self.id, name)

        prompt = TOOL_GENERATION_PROMPT.format(
            name=name,
            description=description,
            input_schema=json.dumps(input_schema, indent=2),
        )

        try:
            self._memory.clear()
            self._memory.add("system", self.system_prompt)
            self._memory.add("user", prompt)

            response = await self.llm_call(use_tools=False)
            content = response.choices[0].message.content or ""  # type: ignore[union-attr]

            # Parse the tool code and test code from the response
            tool_code = _extract_code_block(content, "tool")
            test_code = _extract_code_block(content, "tests")

            if not tool_code or not test_code:
                logger.error("Failed to parse tool/test code from LLM response")
                self.status = AgentStatus.FAILED
                return None

            self.status = AgentStatus.COMPLETED
            return tool_code, test_code

        except Exception as e:
            logger.error("Coder %s failed to generate tool: %s", self.id, e, exc_info=True)
            self.status = AgentStatus.FAILED
            return None


def _extract_code_block(content: str, label: str) -> str | None:
    """Extract a labeled code block from LLM output.

    Matches ```label ... ``` blocks.
    """
    pattern = rf"```{label}\s*\n(.*?)```"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback: try ```python label or just ``` blocks in order
    # (LLMs don't always follow the exact format)
    pattern_alt = rf"```(?:python)?\s*\n(.*?)```"
    blocks = re.findall(pattern_alt, content, re.DOTALL)

    if label == "tool" and len(blocks) >= 1:
        return blocks[0].strip()
    if label == "tests" and len(blocks) >= 2:
        return blocks[1].strip()

    return None
