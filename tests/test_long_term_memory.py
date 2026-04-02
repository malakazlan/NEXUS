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
