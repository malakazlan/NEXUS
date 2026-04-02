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
                metadatas=[metadata] if metadata else None,
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
