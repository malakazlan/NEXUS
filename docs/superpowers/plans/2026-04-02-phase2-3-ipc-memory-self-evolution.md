# Phase 2 Completion + Phase 3: Agent IPC, Long-Term Memory, Self-Evolution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Phase 2 (agent-to-agent messaging, ChromaDB long-term memory) and implement Phase 3 — the killer feature where agents create new MCP tools at runtime when they hit limitations.

**Architecture:** Agent IPC is a thin messaging layer on top of the existing EventBus. Long-term memory wraps ChromaDB for vector storage. Self-evolution adds a DynamicToolCreator that coordinates with the CoderAgent to generate, sandbox-test, and register new MCP tools. A human-approval gate controls tool creation.

**Tech Stack:** Python 3.11+, asyncio, ChromaDB (already in pyproject.toml), existing EventBus, subprocess sandbox

---

## File Map

### Phase 2 Completion (2 files)

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `nexus/agents/messaging.py` | Agent-to-agent IPC: send, receive, broadcast via EventBus |
| Create | `nexus/memory/long_term.py` | ChromaDB vector store: store, query, delete knowledge |

### Phase 3: Self-Evolution (4 files + 1 modify)

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `nexus/mcp_layer/sandbox.py` | Isolated subprocess execution for testing generated tools |
| Create | `nexus/mcp_layer/creator.py` | DynamicToolCreator: spec -> code -> test -> register pipeline |
| Create | `nexus/events/approval.py` | Human-in-the-loop approval gate for tool creation |
| Modify | `nexus/agents/base.py:167-179` | Add `propose_tool()` and `send_message()` methods |
| Modify | `nexus/agents/coder.py` | Add `generate_tool()` method for tool creation |
| Modify | `nexus/kernel/kernel.py:38-55` | Boot: load persisted tools, init ChromaDB, register IPC events |
| Modify | `nexus/config.py` | Add `tools_dir` config for tool persistence path |

### Tests (4 files)

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `tests/test_messaging.py` | Agent IPC tests |
| Create | `tests/test_long_term_memory.py` | ChromaDB memory tests |
| Create | `tests/test_sandbox.py` | Sandbox isolation tests |
| Create | `tests/test_tool_creator.py` | End-to-end tool creation tests |

---

## Task 1: Agent-to-Agent Messaging

**Files:**
- Create: `nexus/agents/messaging.py`
- Create: `tests/test_messaging.py`
- Modify: `nexus/agents/base.py`
- Modify: `nexus/events/types.py`

### Step-by-step:

- [ ] **Step 1: Add MESSAGE event type to events/types.py**

Add a new event type for agent messages. Open `nexus/events/types.py` and add to the `EventType` enum:

```python
    # Agent messaging (IPC)
    AGENT_MESSAGE = "agent.message"
```

Add it after the `AGENT_TERMINATED` line (after line 27).

- [ ] **Step 2: Write the failing test for messaging**

Create `tests/test_messaging.py`:

```python
"""Tests for agent-to-agent messaging via EventBus."""

import asyncio
import pytest
from nexus.events.bus import EventBus
from nexus.events.types import EventType
from nexus.agents.messaging import AgentMessage, MessageRouter


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def router(event_bus):
    return MessageRouter(event_bus)


@pytest.mark.asyncio
async def test_send_and_receive(router):
    """An agent can send a message and the target agent receives it."""
    received = []

    async def handler(msg: AgentMessage):
        received.append(msg)

    router.register_handler("agent-b", handler)
    await router.send(
        from_agent="agent-a",
        to_agent="agent-b",
        content="hello from A",
        message_type="request",
    )
    # Give the event bus time to dispatch
    await asyncio.sleep(0.05)

    assert len(received) == 1
    assert received[0].from_agent == "agent-a"
    assert received[0].to_agent == "agent-b"
    assert received[0].content == "hello from A"
    assert received[0].message_type == "request"


@pytest.mark.asyncio
async def test_broadcast(router):
    """Broadcast sends to all registered handlers."""
    received_b = []
    received_c = []

    async def handler_b(msg: AgentMessage):
        received_b.append(msg)

    async def handler_c(msg: AgentMessage):
        received_c.append(msg)

    router.register_handler("agent-b", handler_b)
    router.register_handler("agent-c", handler_c)

    await router.broadcast(
        from_agent="agent-a",
        content="hello everyone",
    )
    await asyncio.sleep(0.05)

    assert len(received_b) == 1
    assert len(received_c) == 1
    assert received_b[0].content == "hello everyone"
    assert received_b[0].message_type == "broadcast"


@pytest.mark.asyncio
async def test_unregister_handler(router):
    """Unregistered agents do not receive messages."""
    received = []

    async def handler(msg: AgentMessage):
        received.append(msg)

    router.register_handler("agent-b", handler)
    router.unregister_handler("agent-b")

    await router.send(
        from_agent="agent-a",
        to_agent="agent-b",
        content="should not arrive",
        message_type="request",
    )
    await asyncio.sleep(0.05)
    assert len(received) == 0


@pytest.mark.asyncio
async def test_correlation_id_round_trip(router):
    """Request-response pairing via correlation_id."""
    received = []

    async def handler(msg: AgentMessage):
        received.append(msg)

    router.register_handler("agent-b", handler)
    await router.send(
        from_agent="agent-a",
        to_agent="agent-b",
        content="what is 2+2?",
        message_type="request",
        correlation_id="req-001",
    )
    await asyncio.sleep(0.05)

    assert received[0].correlation_id == "req-001"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /d/AGENTS/NEXUS && python -m pytest tests/test_messaging.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'nexus.agents.messaging'`

- [ ] **Step 4: Implement the messaging module**

Create `nexus/agents/messaging.py`:

```python
"""Agent-to-agent messaging (IPC) via the EventBus."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine
from uuid import uuid4

from pydantic import BaseModel, Field

from nexus.events.bus import EventBus
from nexus.events.types import EventType, NexusEvent

logger = logging.getLogger(__name__)

# Handler signature: receives an AgentMessage
MessageHandler = Callable[["AgentMessage"], Coroutine[Any, Any, None]]


class AgentMessage(BaseModel):
    """A message sent between agents."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    from_agent: str
    to_agent: str  # "*" for broadcast
    content: str
    message_type: str = "request"  # request | response | broadcast
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"frozen": True}


class MessageRouter:
    """Routes messages between agents using the EventBus.

    Each agent registers a handler. When a message arrives on the bus
    targeting that agent, the handler is called.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._bus = event_bus
        self._handlers: dict[str, MessageHandler] = {}
        # Subscribe to all agent message events
        self._bus.subscribe(EventType.AGENT_MESSAGE, self._dispatch)

    def register_handler(self, agent_id: str, handler: MessageHandler) -> None:
        self._handlers[agent_id] = handler

    def unregister_handler(self, agent_id: str) -> None:
        self._handlers.pop(agent_id, None)

    async def send(
        self,
        *,
        from_agent: str,
        to_agent: str,
        content: str,
        message_type: str = "request",
        correlation_id: str | None = None,
    ) -> AgentMessage:
        """Send a message from one agent to another."""
        msg = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            correlation_id=correlation_id,
        )
        await self._bus.emit(
            NexusEvent(
                type=EventType.AGENT_MESSAGE,
                source=from_agent,
                data=msg.model_dump(mode="json"),
            )
        )
        return msg

    async def broadcast(
        self,
        *,
        from_agent: str,
        content: str,
    ) -> AgentMessage:
        """Broadcast a message to all registered agents."""
        return await self.send(
            from_agent=from_agent,
            to_agent="*",
            content=content,
            message_type="broadcast",
        )

    async def _dispatch(self, event: NexusEvent) -> None:
        """EventBus callback: route message to the target handler."""
        msg = AgentMessage(**event.data)

        if msg.to_agent == "*":
            # Broadcast to all handlers (except sender)
            for agent_id, handler in self._handlers.items():
                if agent_id != msg.from_agent:
                    try:
                        await handler(msg)
                    except Exception as e:
                        logger.error("Message handler error for %s: %s", agent_id, e)
        else:
            handler = self._handlers.get(msg.to_agent)
            if handler:
                try:
                    await handler(msg)
                except Exception as e:
                    logger.error("Message handler error for %s: %s", msg.to_agent, e)
            else:
                logger.warning("No handler for agent %s, message dropped", msg.to_agent)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /d/AGENTS/NEXUS && python -m pytest tests/test_messaging.py -v`
Expected: 4 tests PASS

- [ ] **Step 6: Add send_message() to BaseAgent**

In `nexus/agents/base.py`, add these methods after the `to_dict()` method (after line 179):

```python
    # ── Messaging ────────────────────────────────────────────────────

    async def send_message(
        self,
        to_agent: str,
        content: str,
        *,
        message_type: str = "request",
        correlation_id: str | None = None,
    ) -> None:
        """Send a message to another agent via the kernel's message router."""
        if self._kernel.message_router is None:
            logger.warning("Message router not available, message dropped")
            return
        await self._kernel.message_router.send(
            from_agent=self.id,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            correlation_id=correlation_id,
        )
```

- [ ] **Step 7: Add message_router to Kernel**

In `nexus/kernel/kernel.py`, add the import at the top (after line 6):

```python
from nexus.agents.messaging import MessageRouter
```

In `Kernel.__init__` (around line 34), add after `self.shared_memory`:

```python
        self.message_router = MessageRouter(self.event_bus)
```

- [ ] **Step 8: Commit**

```bash
cd /d/AGENTS/NEXUS
git add nexus/agents/messaging.py nexus/events/types.py nexus/agents/base.py nexus/kernel/kernel.py tests/test_messaging.py
git commit -m "feat: add agent-to-agent messaging via EventBus IPC"
```

---

## Task 2: ChromaDB Long-Term Memory

**Files:**
- Create: `nexus/memory/long_term.py`
- Create: `tests/test_long_term_memory.py`
- Modify: `nexus/kernel/kernel.py`

### Step-by-step:

- [ ] **Step 1: Write the failing test**

Create `tests/test_long_term_memory.py`:

```python
"""Tests for ChromaDB-backed long-term memory."""

import pytest
from nexus.memory.long_term import LongTermMemory


@pytest.fixture
def memory():
    """Create a fresh in-memory LongTermMemory for each test."""
    mem = LongTermMemory(persist_dir=None)  # in-memory, no disk
    yield mem


@pytest.mark.asyncio
async def test_store_and_query(memory):
    """Store a document and retrieve it by semantic search."""
    await memory.store(
        doc_id="doc-1",
        content="MCP is a protocol for connecting AI models to tools",
        metadata={"source": "researcher-001", "task_id": "task-abc"},
    )
    results = await memory.query("What protocol connects AI to tools?", n_results=1)

    assert len(results) == 1
    assert results[0]["id"] == "doc-1"
    assert "MCP" in results[0]["content"]
    assert results[0]["metadata"]["source"] == "researcher-001"


@pytest.mark.asyncio
async def test_store_multiple_and_rank(memory):
    """Store multiple docs and verify the most relevant is returned first."""
    await memory.store("doc-1", "Python is a programming language")
    await memory.store("doc-2", "ChromaDB is a vector database for embeddings")
    await memory.store("doc-3", "FastAPI is a web framework for building APIs")

    results = await memory.query("vector database", n_results=2)
    assert len(results) == 2
    assert results[0]["id"] == "doc-2"  # most relevant


@pytest.mark.asyncio
async def test_delete(memory):
    """Deleted documents are not returned in queries."""
    await memory.store("doc-1", "This will be deleted")
    await memory.store("doc-2", "This will stay")

    await memory.delete("doc-1")
    results = await memory.query("deleted", n_results=5)

    ids = [r["id"] for r in results]
    assert "doc-1" not in ids


@pytest.mark.asyncio
async def test_list_by_metadata(memory):
    """Filter documents by metadata."""
    await memory.store("doc-1", "Research about AI", metadata={"agent": "researcher-1"})
    await memory.store("doc-2", "Code review notes", metadata={"agent": "coder-1"})
    await memory.store("doc-3", "More research", metadata={"agent": "researcher-1"})

    results = await memory.list_by_metadata({"agent": "researcher-1"})
    assert len(results) == 2
    ids = {r["id"] for r in results}
    assert ids == {"doc-1", "doc-3"}


@pytest.mark.asyncio
async def test_clear(memory):
    """Clear removes all documents."""
    await memory.store("doc-1", "content 1")
    await memory.store("doc-2", "content 2")
    await memory.clear()

    results = await memory.query("content", n_results=10)
    assert len(results) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /d/AGENTS/NEXUS && python -m pytest tests/test_long_term_memory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'nexus.memory.long_term'`

- [ ] **Step 3: Implement long-term memory**

Create `nexus/memory/long_term.py`:

```python
"""Long-term memory backed by ChromaDB vector store."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import chromadb

logger = logging.getLogger(__name__)

# Default collection name for NEXUS knowledge
_COLLECTION_NAME = "nexus_knowledge"


class LongTermMemory:
    """Persistent vector store for agent knowledge.

    Agents store research findings, code patterns, and decisions here.
    Semantic search lets any agent query "what do we know about X?"

    Args:
        persist_dir: Directory for ChromaDB persistence. None = in-memory (for tests).
        collection_name: ChromaDB collection name.
    """

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str = _COLLECTION_NAME,
    ) -> None:
        if persist_dir is None:
            self._client = chromadb.Client()
        else:
            self._client = chromadb.PersistentClient(path=persist_dir)

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "LongTermMemory initialized (persist=%s, collection=%s, docs=%d)",
            persist_dir or "in-memory",
            collection_name,
            self._collection.count(),
        )

    async def store(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a document in the vector store.

        Uses ChromaDB's built-in default embedding function.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._collection.upsert(
                ids=[doc_id],
                documents=[content],
                metadatas=[metadata or {}],
            ),
        )
        logger.debug("Stored doc %s (%d chars)", doc_id, len(content))

    async def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search over stored documents.

        Returns list of dicts with keys: id, content, metadata, distance.
        """
        if self._collection.count() == 0:
            return []

        loop = asyncio.get_event_loop()
        kwargs: dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": min(n_results, self._collection.count()),
        }
        if where:
            kwargs["where"] = where

        result = await loop.run_in_executor(
            None,
            lambda: self._collection.query(**kwargs),
        )

        docs: list[dict[str, Any]] = []
        if result["ids"] and result["ids"][0]:
            for i, doc_id in enumerate(result["ids"][0]):
                docs.append({
                    "id": doc_id,
                    "content": result["documents"][0][i] if result["documents"] else "",
                    "metadata": result["metadatas"][0][i] if result["metadatas"] else {},
                    "distance": result["distances"][0][i] if result["distances"] else 0.0,
                })
        return docs

    async def delete(self, doc_id: str) -> None:
        """Delete a document by ID."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._collection.delete(ids=[doc_id]),
        )

    async def list_by_metadata(
        self, where: dict[str, Any], limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List documents matching a metadata filter."""
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._collection.get(where=where, limit=limit),
        )

        docs: list[dict[str, Any]] = []
        if result["ids"]:
            for i, doc_id in enumerate(result["ids"]):
                docs.append({
                    "id": doc_id,
                    "content": result["documents"][i] if result["documents"] else "",
                    "metadata": result["metadatas"][i] if result["metadatas"] else {},
                })
        return docs

    async def clear(self) -> None:
        """Delete all documents in the collection."""
        loop = asyncio.get_event_loop()
        # ChromaDB doesn't have a clear() — delete and recreate
        name = self._collection.name
        metadata = self._collection.metadata
        await loop.run_in_executor(
            None,
            lambda: self._client.delete_collection(name),
        )
        self._collection = self._client.get_or_create_collection(
            name=name, metadata=metadata,
        )

    @property
    def count(self) -> int:
        return self._collection.count()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /d/AGENTS/NEXUS && python -m pytest tests/test_long_term_memory.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Wire LongTermMemory into Kernel**

In `nexus/kernel/kernel.py`, add the import at top:

```python
from nexus.memory.long_term import LongTermMemory
```

In `Kernel.__init__`, add after `self.message_router`:

```python
        self.long_term_memory: LongTermMemory | None = None
```

In `Kernel.boot()`, add before `self._booted = True`:

```python
        # Initialize long-term memory (ChromaDB)
        persist_dir = str(self.config.workspace_dir / "chromadb")
        self.long_term_memory = LongTermMemory(persist_dir=persist_dir)
```

- [ ] **Step 6: Commit**

```bash
cd /d/AGENTS/NEXUS
git add nexus/memory/long_term.py nexus/kernel/kernel.py tests/test_long_term_memory.py
git commit -m "feat: add ChromaDB long-term memory for persistent agent knowledge"
```

---

## Task 3: Sandbox for Safe Tool Testing

**Files:**
- Create: `nexus/mcp_layer/sandbox.py`
- Create: `tests/test_sandbox.py`

### Step-by-step:

- [ ] **Step 1: Write the failing test**

Create `tests/test_sandbox.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /d/AGENTS/NEXUS && python -m pytest tests/test_sandbox.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'nexus.mcp_layer.sandbox'`

- [ ] **Step 3: Implement the sandbox**

Create `nexus/mcp_layer/sandbox.py`:

```python
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

    # Match pytest summary line like "3 passed" or "1 failed, 2 passed"
    match = re.search(r"(\d+) passed", output)
    if match:
        passed = int(match.group(1))

    match = re.search(r"(\d+) failed", output)
    if match:
        failed = int(match.group(1))

    return passed, failed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /d/AGENTS/NEXUS && python -m pytest tests/test_sandbox.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /d/AGENTS/NEXUS
git add nexus/mcp_layer/sandbox.py tests/test_sandbox.py
git commit -m "feat: add sandbox for isolated tool code testing"
```

---

## Task 4: Human Approval Gate

**Files:**
- Create: `nexus/events/approval.py`

### Step-by-step:

- [ ] **Step 1: Implement the approval gate**

Create `nexus/events/approval.py`:

```python
"""Human-in-the-loop approval gate.

When an action requires approval (e.g., tool creation), an approval.requested
event is emitted and the caller awaits the response. The CLI or dashboard
listens for these events and prompts the user.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from nexus.events.bus import EventBus
from nexus.events.types import EventType, NexusEvent

logger = logging.getLogger(__name__)


class ApprovalGate:
    """Manages human approval requests and responses.

    Usage:
        approved = await gate.request(
            action="tool.create",
            description="Create csv_parser tool",
            details={...},
            source="coder-abc123",
        )
        if approved:
            # proceed
    """

    def __init__(self, event_bus: EventBus, *, auto_approve: bool = False) -> None:
        self._bus = event_bus
        self._auto_approve = auto_approve
        self._pending: dict[str, asyncio.Future[bool]] = {}

        # Listen for approval responses
        self._bus.subscribe(EventType.APPROVAL_GRANTED, self._on_granted)
        self._bus.subscribe(EventType.APPROVAL_DENIED, self._on_denied)

    async def request(
        self,
        *,
        action: str,
        description: str,
        details: dict[str, Any] | None = None,
        source: str = "kernel",
        timeout: float = 300.0,
    ) -> bool:
        """Request human approval. Blocks until approved/denied or timeout.

        Returns True if approved, False if denied or timed out.
        """
        if self._auto_approve:
            logger.info("Auto-approving: %s — %s", action, description)
            return True

        # Create a future to await the response
        loop = asyncio.get_event_loop()
        future: asyncio.Future[bool] = loop.create_future()

        event = NexusEvent(
            type=EventType.APPROVAL_REQUESTED,
            source=source,
            data={
                "action": action,
                "description": description,
                "details": details or {},
            },
        )

        self._pending[event.id] = future

        # Emit the request event
        await self._bus.emit(event)
        logger.info("Approval requested [%s]: %s — %s", event.id, action, description)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Approval request %s timed out after %.0fs", event.id, timeout)
            self._pending.pop(event.id, None)
            return False

    async def respond(self, request_id: str, approved: bool) -> None:
        """Respond to a pending approval request (called by CLI/dashboard)."""
        if approved:
            await self._bus.emit(
                NexusEvent(
                    type=EventType.APPROVAL_GRANTED,
                    source="human",
                    data={"request_id": request_id},
                )
            )
        else:
            await self._bus.emit(
                NexusEvent(
                    type=EventType.APPROVAL_DENIED,
                    source="human",
                    data={"request_id": request_id},
                )
            )

    async def _on_granted(self, event: NexusEvent) -> None:
        request_id = event.data.get("request_id", "")
        future = self._pending.pop(request_id, None)
        if future and not future.done():
            future.set_result(True)
            logger.info("Approval granted: %s", request_id)

    async def _on_denied(self, event: NexusEvent) -> None:
        request_id = event.data.get("request_id", "")
        future = self._pending.pop(request_id, None)
        if future and not future.done():
            future.set_result(False)
            logger.info("Approval denied: %s", request_id)
```

- [ ] **Step 2: Wire ApprovalGate into Kernel**

In `nexus/kernel/kernel.py`, add import:

```python
from nexus.events.approval import ApprovalGate
```

In `Kernel.__init__`, add after `self.long_term_memory`:

```python
        self.approval_gate: ApprovalGate | None = None
```

In `Kernel.boot()`, add before `self._booted = True`:

```python
        # Initialize approval gate
        auto_approve = not self.config.require_approval_for_tools
        self.approval_gate = ApprovalGate(self.event_bus, auto_approve=auto_approve)
```

- [ ] **Step 3: Commit**

```bash
cd /d/AGENTS/NEXUS
git add nexus/events/approval.py nexus/kernel/kernel.py
git commit -m "feat: add human-in-the-loop approval gate for tool creation"
```

---

## Task 5: Dynamic Tool Creator (Self-Evolution Core)

**Files:**
- Create: `nexus/mcp_layer/creator.py`
- Create: `tests/test_tool_creator.py`
- Modify: `nexus/config.py`

### Step-by-step:

- [ ] **Step 1: Add tools_dir to config**

In `nexus/config.py`, add after the `workspace_dir` field (after line 28):

```python
    # Persisted dynamic tools
    tools_dir: Path = Path.home() / ".nexus" / "tools"
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_tool_creator.py`:

```python
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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /d/AGENTS/NEXUS && python -m pytest tests/test_tool_creator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'nexus.mcp_layer.creator'`

- [ ] **Step 4: Implement the DynamicToolCreator**

Create `nexus/mcp_layer/creator.py`:

```python
"""DynamicToolCreator — the self-evolution engine.

Pipeline: ToolSpec + code → sandbox test → persist → register as MCP tool.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from nexus.events.approval import ApprovalGate
from nexus.events.bus import EventBus
from nexus.events.types import EventType, NexusEvent
from nexus.mcp_layer.registry import ToolRegistry
from nexus.mcp_layer.sandbox import Sandbox, SandboxResult

logger = logging.getLogger(__name__)


class ToolSpec(BaseModel):
    """Specification for a dynamically created tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] = Field(default_factory=dict)
    proposed_by: str  # agent_id that requested this tool


class ToolCreationResult(BaseModel):
    """Result of the tool creation pipeline."""

    success: bool
    tool_name: str
    error: str | None = None
    sandbox_result: dict[str, Any] | None = None


class DynamicToolCreator:
    """Creates, tests, persists, and registers new MCP tools at runtime.

    This is the core of NEXUS self-evolution. When an agent proposes a new tool:
    1. Human approval is requested (if enabled)
    2. Code is tested in the sandbox
    3. If tests pass, tool is persisted to disk
    4. Tool is registered in the ToolRegistry, available to all agents
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        tool_registry: ToolRegistry,
        sandbox: Sandbox,
        approval_gate: ApprovalGate,
        tools_dir: Path,
    ) -> None:
        self._bus = event_bus
        self._registry = tool_registry
        self._sandbox = sandbox
        self._approval = approval_gate
        self._tools_dir = tools_dir
        self._tools_dir.mkdir(parents=True, exist_ok=True)

    async def create_tool(
        self,
        spec: ToolSpec,
        tool_code: str,
        test_code: str,
    ) -> ToolCreationResult:
        """Full pipeline: approve → test → persist → register.

        Args:
            spec: Tool specification (name, description, schema).
            tool_code: Python source for the tool function.
                       Must define an async function matching spec.name.
            test_code: Pytest test file source. Tests import from `tool`.

        Returns:
            ToolCreationResult with success status and details.
        """
        # 1. Emit proposal event
        await self._bus.emit(
            NexusEvent(
                type=EventType.TOOL_PROPOSED,
                source=spec.proposed_by,
                data={"tool_name": spec.name, "description": spec.description},
            )
        )

        # 2. Request human approval
        approved = await self._approval.request(
            action="tool.create",
            description=f"Create tool '{spec.name}': {spec.description}",
            details={"spec": spec.model_dump(), "code_length": len(tool_code)},
            source=spec.proposed_by,
        )

        if not approved:
            logger.info("Tool creation denied: %s", spec.name)
            return ToolCreationResult(
                success=False,
                tool_name=spec.name,
                error="Human approval denied",
            )

        # 3. Test in sandbox
        await self._bus.emit(
            NexusEvent(
                type=EventType.TOOL_TESTING,
                source=spec.proposed_by,
                data={"tool_name": spec.name},
            )
        )

        sandbox_result = await self._sandbox.run_tests(tool_code, test_code)

        if not sandbox_result.success:
            logger.warning(
                "Tool %s failed sandbox tests: %d passed, %d failed",
                spec.name,
                sandbox_result.tests_passed,
                sandbox_result.tests_failed,
            )
            await self._bus.emit(
                NexusEvent(
                    type=EventType.TOOL_FAILED,
                    source=spec.proposed_by,
                    data={
                        "tool_name": spec.name,
                        "tests_passed": sandbox_result.tests_passed,
                        "tests_failed": sandbox_result.tests_failed,
                        "stderr": sandbox_result.stderr[:500],
                    },
                )
            )
            return ToolCreationResult(
                success=False,
                tool_name=spec.name,
                error=f"Sandbox tests failed: {sandbox_result.tests_failed} failures",
                sandbox_result={
                    "stdout": sandbox_result.stdout,
                    "stderr": sandbox_result.stderr,
                    "tests_passed": sandbox_result.tests_passed,
                    "tests_failed": sandbox_result.tests_failed,
                },
            )

        # 4. Persist to disk
        self._persist_tool(spec, tool_code, test_code)

        # 5. Register in the tool registry
        func = self._load_tool_function(spec.name, tool_code)
        self._registry.register(
            name=spec.name,
            description=spec.description,
            input_schema=spec.input_schema,
            func=func,
            output_schema=spec.output_schema,
            is_builtin=False,
            created_by=spec.proposed_by,
        )

        await self._bus.emit(
            NexusEvent(
                type=EventType.TOOL_CREATED,
                source=spec.proposed_by,
                data={
                    "tool_name": spec.name,
                    "tests_passed": sandbox_result.tests_passed,
                },
            )
        )

        logger.info(
            "Tool created: %s (by %s, %d tests passed)",
            spec.name,
            spec.proposed_by,
            sandbox_result.tests_passed,
        )
        return ToolCreationResult(success=True, tool_name=spec.name)

    async def load_persisted_tools(
        self, registry: ToolRegistry | None = None,
    ) -> int:
        """Load all persisted tools from disk into the registry.

        Called at kernel boot to restore tools from previous sessions.
        Returns the number of tools loaded.
        """
        target = registry or self._registry
        loaded = 0

        if not self._tools_dir.exists():
            return 0

        for tool_dir in self._tools_dir.iterdir():
            if not tool_dir.is_dir():
                continue

            manifest_path = tool_dir / "manifest.json"
            tool_path = tool_dir / "tool.py"

            if not manifest_path.exists() or not tool_path.exists():
                continue

            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                tool_code = tool_path.read_text(encoding="utf-8")

                func = self._load_tool_function(manifest["name"], tool_code)
                target.register(
                    name=manifest["name"],
                    description=manifest["description"],
                    input_schema=manifest["input_schema"],
                    func=func,
                    output_schema=manifest.get("output_schema", {}),
                    is_builtin=False,
                    created_by=manifest.get("created_by"),
                )
                loaded += 1
                logger.info("Loaded persisted tool: %s", manifest["name"])
            except Exception as e:
                logger.error("Failed to load tool from %s: %s", tool_dir, e)

        return loaded

    def _persist_tool(
        self, spec: ToolSpec, tool_code: str, test_code: str,
    ) -> None:
        """Save tool code, tests, and manifest to disk."""
        tool_dir = self._tools_dir / spec.name
        tool_dir.mkdir(parents=True, exist_ok=True)

        (tool_dir / "tool.py").write_text(tool_code, encoding="utf-8")
        (tool_dir / "tests.py").write_text(test_code, encoding="utf-8")

        manifest = {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_schema,
            "output_schema": spec.output_schema,
            "proposed_by": spec.proposed_by,
            "created_by": spec.proposed_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (tool_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8",
        )
        logger.info("Persisted tool to %s", tool_dir)

    @staticmethod
    def _load_tool_function(name: str, source_code: str):
        """Dynamically load a tool function from source code string.

        Creates a module from the source and extracts the named function.
        """
        module_name = f"nexus_dynamic_tool_{name}"

        # Remove module if it was previously loaded (hot reload)
        if module_name in sys.modules:
            del sys.modules[module_name]

        spec = importlib.util.spec_from_loader(module_name, loader=None)
        module = importlib.util.module_from_spec(spec)
        exec(compile(source_code, f"<tool:{name}>", "exec"), module.__dict__)
        sys.modules[module_name] = module

        func = getattr(module, name, None)
        if func is None:
            raise ValueError(
                f"Tool source must define a function named '{name}', "
                f"but found: {[k for k in module.__dict__ if not k.startswith('_')]}"
            )
        return func
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /d/AGENTS/NEXUS && python -m pytest tests/test_tool_creator.py -v`
Expected: 4 tests PASS

- [ ] **Step 6: Wire DynamicToolCreator into Kernel**

In `nexus/kernel/kernel.py`, add imports:

```python
from nexus.mcp_layer.sandbox import Sandbox
from nexus.mcp_layer.creator import DynamicToolCreator
```

In `Kernel.__init__`, add after `self.approval_gate`:

```python
        self.tool_creator: DynamicToolCreator | None = None
```

In `Kernel.boot()`, add before `self._booted = True`:

```python
        # Initialize tool creator (self-evolution engine)
        sandbox = Sandbox(
            workspace=self.config.workspace_dir / "sandbox",
            timeout=self.config.tool_creation_timeout,
        )
        self.tool_creator = DynamicToolCreator(
            event_bus=self.event_bus,
            tool_registry=self.tool_registry,
            sandbox=sandbox,
            approval_gate=self.approval_gate,
            tools_dir=self.config.tools_dir,
        )

        # Load persisted tools from previous sessions
        loaded = await self.tool_creator.load_persisted_tools()
        if loaded:
            logger.info("Loaded %d persisted dynamic tools", loaded)
```

- [ ] **Step 7: Commit**

```bash
cd /d/AGENTS/NEXUS
git add nexus/mcp_layer/creator.py nexus/config.py nexus/kernel/kernel.py tests/test_tool_creator.py
git commit -m "feat: add DynamicToolCreator — the self-evolution engine"
```

---

## Task 6: Wire propose_tool() into Agents

**Files:**
- Modify: `nexus/agents/base.py`
- Modify: `nexus/agents/coder.py`

### Step-by-step:

- [ ] **Step 1: Add propose_tool() to BaseAgent**

In `nexus/agents/base.py`, add this method after the `send_message()` method you added in Task 1:

```python
    # ── Self-evolution ───────────────────────────────────────────────

    async def propose_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        reason: str = "",
    ) -> bool:
        """Propose a new tool when the agent hits a limitation.

        The orchestrator or coder agent will then generate the implementation.
        Returns True if the tool was successfully created.
        """
        if self._kernel.tool_registry.has(name):
            logger.info("Tool %s already exists, skipping proposal", name)
            return True

        if self._kernel.tool_creator is None:
            logger.warning("Tool creator not available, cannot propose tool %s", name)
            return False

        logger.info(
            "Agent %s proposing tool: %s (reason: %s)",
            self.id, name, reason or "not specified",
        )

        # Ask the coder agent to generate the implementation
        from nexus.agents.coder import CoderAgent

        coder_agents = self._kernel.agent_registry.find_by_type("coder")
        if coder_agents:
            coder = coder_agents[0]
        else:
            coder = CoderAgent(kernel=self._kernel)
            await self._kernel.spawn_agent(coder)

        generation_result = await coder.generate_tool(
            name=name,
            description=description,
            input_schema=input_schema,
        )

        if generation_result is None:
            logger.error("Coder failed to generate tool %s", name)
            return False

        tool_code, test_code = generation_result

        from nexus.mcp_layer.creator import ToolSpec

        spec = ToolSpec(
            name=name,
            description=description,
            input_schema=input_schema,
            proposed_by=self.id,
        )

        result = await self._kernel.tool_creator.create_tool(spec, tool_code, test_code)
        return result.success
```

- [ ] **Step 2: Add generate_tool() to CoderAgent**

Replace the full content of `nexus/agents/coder.py` with:

```python
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
```

- [ ] **Step 3: Commit**

```bash
cd /d/AGENTS/NEXUS
git add nexus/agents/base.py nexus/agents/coder.py
git commit -m "feat: wire propose_tool() into agents and add CoderAgent.generate_tool()"
```

---

## Task 7: Load Persisted Tools on Kernel Boot + Final Wiring

**Files:**
- Modify: `nexus/kernel/kernel.py`
- Modify: `nexus/api/routes/tools.py` (add route for dynamic tools)

### Step-by-step:

- [ ] **Step 1: Read current tools route**

Read `nexus/api/routes/tools.py` to see the current implementation.

- [ ] **Step 2: Add dynamic tool info to the tools API route**

In `nexus/api/routes/tools.py`, ensure the response includes `is_builtin` and `created_by` fields. If the current implementation already serializes `RegisteredTool` fields, this may already work. Verify by reading the file.

Add a POST endpoint for triggering tool creation via API:

Add to the tools route file:

```python
from pydantic import BaseModel

class ToolCreateRequest(BaseModel):
    name: str
    description: str
    input_schema: dict
    tool_code: str
    test_code: str


@router.post("/api/tools", status_code=201)
async def create_tool(req: ToolCreateRequest):
    """Create a dynamic tool via the API (for testing/manual use)."""
    if _kernel is None or _kernel.tool_creator is None:
        raise HTTPException(status_code=503, detail="Tool creator not available")

    from nexus.mcp_layer.creator import ToolSpec

    spec = ToolSpec(
        name=req.name,
        description=req.description,
        input_schema=req.input_schema,
        proposed_by="api",
    )
    result = await _kernel.tool_creator.create_tool(spec, req.tool_code, req.test_code)

    if result.success:
        return {"status": "created", "tool_name": result.tool_name}
    raise HTTPException(status_code=400, detail=result.error or "Tool creation failed")
```

- [ ] **Step 3: Verify all Kernel.boot() wiring is correct**

The final `Kernel.boot()` method should now do all of this in order:
1. Register built-in tools
2. Create workspace directory
3. Initialize ChromaDB long-term memory
4. Initialize approval gate
5. Initialize sandbox + DynamicToolCreator
6. Load persisted dynamic tools
7. Emit KERNEL_BOOT event

Read `nexus/kernel/kernel.py` and verify the boot sequence is correct and complete.

- [ ] **Step 4: Commit**

```bash
cd /d/AGENTS/NEXUS
git add nexus/kernel/kernel.py nexus/api/routes/tools.py
git commit -m "feat: complete Phase 3 wiring — boot loads persisted tools, API exposes tool creation"
```

---

## Task 8: Integration Test — End-to-End Self-Evolution

**Files:**
- Create: `tests/test_self_evolution_e2e.py`

### Step-by-step:

- [ ] **Step 1: Write the end-to-end test**

Create `tests/test_self_evolution_e2e.py`:

```python
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
    """Boot kernel → create tool → verify it works → shutdown → reboot → tool still there."""
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
```

- [ ] **Step 2: Run the test**

Run: `cd /d/AGENTS/NEXUS && python -m pytest tests/test_self_evolution_e2e.py -v`
Expected: PASS (this test does NOT call any LLM — it provides code directly to the creator)

- [ ] **Step 3: Commit**

```bash
cd /d/AGENTS/NEXUS
git add tests/test_self_evolution_e2e.py
git commit -m "test: add end-to-end self-evolution integration test"
```

---

## Task 9: Run All Tests

### Step-by-step:

- [ ] **Step 1: Run the full test suite**

Run: `cd /d/AGENTS/NEXUS && python -m pytest tests/ -v`
Expected: All tests pass — messaging, long-term memory, sandbox, tool creator, e2e, boot.

- [ ] **Step 2: Fix any failures**

If any test fails, diagnose and fix. Do not skip tests.

- [ ] **Step 3: Final commit**

```bash
cd /d/AGENTS/NEXUS
git add -A
git commit -m "feat: complete Phase 2+3 — agent IPC, long-term memory, self-evolution"
```

---

## Verification Checklist

After all tasks are complete, verify:

- [ ] `python -m pytest tests/ -v` — all tests pass
- [ ] `nexus start` — boots without errors, loads persisted tools
- [ ] Event bus carries AGENT_MESSAGE events for IPC
- [ ] LongTermMemory stores and queries via ChromaDB
- [ ] Sandbox isolates tool code in subprocess
- [ ] DynamicToolCreator: spec → sandbox test → persist → register
- [ ] Approval gate blocks when `require_approval_for_tools=True`
- [ ] Persisted tools in `~/.nexus/tools/` survive kernel restart
- [ ] `BaseAgent.propose_tool()` triggers the full self-evolution pipeline
- [ ] `CoderAgent.generate_tool()` produces code + tests from a spec
- [ ] API: `POST /api/tools` creates a dynamic tool
