"""Qdrant vector database provider for Synapse."""

from __future__ import annotations

from typing import Any, Union

from langchain_core.documents import Document

from synapse.database.base import BaseVectorDB
from synapse.embeddings import resolve_embedding


class QdrantDB(BaseVectorDB):
    """Qdrant vector database adapter supporting local memory, disk, or remote cloud cluster."""

    def __init__(
        self,
        location: str | None = ":memory:",
        url: str | None = None,
        api_key: str | None = None,
        path: str | None = None,
        collection_name: str = "synapse_collection",
        embedding: Union[str, Any] | None = None,
        embedding_model: str | None = None,
        embedding_function: Any | None = None,
        **kwargs: Any,
    ) -> None:
        self.collection_name = collection_name
        self.url = url
        self.location = location
        self.api_key = api_key
        self.path = path
        self.embedding_function = resolve_embedding(
            embedding=embedding or embedding_function or embedding_model,
            **kwargs,
        )

        try:
            from langchain_community.vectorstores import Qdrant
            from qdrant_client import QdrantClient

            if url is not None:
                self.client = QdrantClient(url=url, api_key=api_key)
            elif path is not None:
                self.client = QdrantClient(path=path)
            else:
                self.client = QdrantClient(location=location or ":memory:")

            self.store = Qdrant(
                client=self.client,
                collection_name=collection_name,
                embeddings=self.embedding_function,
            )
        except ImportError:
            # Fallback wrapper if qdrant-client is not installed
            from synapse.database.memory import InMemoryDB
            self._fallback = InMemoryDB(
                embedding_model=embedding_model,
                embedding_function=self.embedding_function,
            )
            self.store = None

    def add_documents(
        self,
        documents: list[Document],
        embeddings: list[list[float]] | None = None,
    ) -> list[str]:
        if self.store:
            return self.store.add_documents(documents)
        return self._fallback.add_documents(documents, embeddings)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter_dict: dict[str, Any] | None = None,
        query_embedding: list[float] | None = None,
    ) -> list[Document]:
        if self.store:
            if filter_dict:
                return self.store.similarity_search(query=query, k=k, filter=filter_dict)
            return self.store.similarity_search(query=query, k=k)
        return self._fallback.similarity_search(query=query, k=k, filter_dict=filter_dict)

    def count(self) -> int:
        if self.store:
            try:
                res = self.client.get_collection(self.collection_name)
                return (
                    getattr(res, "points_count", None)
                    or getattr(res, "vectors_count", 0)
                    or getattr(res, "indexed_vectors_count", 0)
                    or 0
                )
            except Exception:
                return 0
        return self._fallback.count()

    def clear(self) -> None:
        if self.store:
            try:
                self.client.delete_collection(self.collection_name)
            except Exception:
                pass  # nosec B110
        else:
            self._fallback.clear()


def qdrant(
    location: str | None = ":memory:",
    url: str | None = None,
    api_key: str | None = None,
    path: str | None = None,
    collection_name: str = "synapse_collection",
    embedding: Union[str, Any] | None = None,
    embedding_model: str | None = None,
    embedding_function: Any | None = None,
    **kwargs: Any,
) -> QdrantDB:
    """Factory helper to configure a Qdrant vector database instance.

    Example:
        ```python
        from synapse.database import qdrant

        # In-memory with MiniLM:
        db = qdrant(embedding="minilm")

        # Local disk with FastEmbed BGE:
        db = qdrant(path="data/qdrant_db", embedding="fastembed")

        # Remote cluster:
        db = qdrant(url="https://xyz.cloud.qdrant.io", api_key="...", embedding="minilm")
        ```
    """
    return QdrantDB(
        location=location,
        url=url,
        api_key=api_key,
        path=path,
        collection_name=collection_name,
        embedding=embedding,
        embedding_model=embedding_model,
        embedding_function=embedding_function,
        **kwargs,
    )


__all__ = ["QdrantDB", "qdrant"]
