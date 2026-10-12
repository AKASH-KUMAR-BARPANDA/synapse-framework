"""ChromaDB vector database provider for Synapse."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb as native_chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document

from synapse.config import (
    DEFAULT_CHROMA_COLLECTION,
    DEFAULT_CHROMA_DIR,
)
from synapse.database.base import BaseVectorDB
from synapse.embeddings import resolve_embedding


class ChromaDB(BaseVectorDB):
    """ChromaDB vector database adapter supporting local disk, in-memory, or remote HTTP."""

    def __init__(
        self,
        path: str | Path | None = None,
        host: str | None = None,
        port: int | None = None,
        ssl: bool = False,
        headers: dict[str, str] | None = None,
        in_memory: bool = False,
        collection_name: str = DEFAULT_CHROMA_COLLECTION,
        embedding: str | Any | None = None,
        embedding_model: str | None = None,
        embedding_function: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Initializes ChromaDB adapter.

        Args:
            path: Local storage path. If ':memory:' or in_memory=True, runs purely in RAM.
            host: Hostname for online/remote ChromaDB server (e.g. 'localhost' or 'api.chroma.io').
            port: Port for remote ChromaDB server (e.g. 8000).
            ssl: Whether to use HTTPS for remote ChromaDB server.
            headers: Optional HTTP headers for remote ChromaDB server (e.g. auth tokens).
            in_memory: If True, operates in ephemeral RAM with zero disk writes.
            collection_name: ChromaDB collection name. Defaults to 'synapse_memory'.
            embedding: Embedding model name ('fastembed', 'minilm', 'openai', etc.) or Embeddings object.
            embedding_model: Backward-compatible alias for embedding model name.
            embedding_function: Optional custom embedding function.
            **kwargs: Extra parameters forwarded to the embedding resolver.
        """
        self.collection_name = collection_name
        self.embedding_function = resolve_embedding(
            embedding=embedding or embedding_function or embedding_model,
            **kwargs,
        )

        if host is not None:
            # Online / remote ChromaDB server
            self.client = native_chromadb.HttpClient(
                host=host,
                port=port or 8000,
                ssl=ssl,
                headers=headers,
            )
        elif in_memory or path == ":memory:":
            # Pure in-memory ephemeral client (0 disk writes)
            self.client = native_chromadb.EphemeralClient()
        else:
            # Local persistent on-disk ChromaDB
            resolved_path = Path(path or DEFAULT_CHROMA_DIR).resolve()
            resolved_path.mkdir(parents=True, exist_ok=True)
            self.client = native_chromadb.PersistentClient(path=str(resolved_path))

        self.store = Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embedding_function,
        )

    def add_documents(
        self,
        documents: list[Document],
        embeddings: list[list[float]] | None = None,
    ) -> list[str]:
        """Upserts documents into ChromaDB."""
        if not documents:
            return []

        ids: list[str] | None = None
        has_chunk_ids = all("chunk_id" in doc.metadata for doc in documents)
        if has_chunk_ids:
            ids = [str(doc.metadata["chunk_id"]) for doc in documents]

        return self.store.add_documents(documents=documents, ids=ids)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter_dict: dict[str, Any] | None = None,
        query_embedding: list[float] | None = None,
    ) -> list[Document]:
        """Performs semantic search in ChromaDB."""
        return self.store.similarity_search(query=query, k=k, filter=filter_dict)

    def count(self) -> int:
        """Returns total document count in the collection."""
        try:
            col = self.client.get_collection(self.collection_name)
            return col.count()
        except Exception:
            return 0

    def clear(self) -> None:
        """Deletes and recreates the collection."""
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass  # nosec B110
        self.store = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embedding_function,
        )


def chromadb(
    path: str | Path | None = None,
    host: str | None = None,
    port: int | None = None,
    ssl: bool = False,
    headers: dict[str, str] | None = None,
    in_memory: bool = False,
    collection_name: str = DEFAULT_CHROMA_COLLECTION,
    embedding: str | Any | None = None,
    embedding_model: str | None = None,
    embedding_function: Any | None = None,
    **kwargs: Any,
) -> ChromaDB:
    """Factory helper to configure a ChromaDB vector database instance.

    Example:
        ```python
        from synapse.database import chromadb
        from synapse.storage import vectorStorage

        # Local persistent with MiniLM:
        db = chromadb("data/chroma_db", embedding="minilm")

        # In-memory ephemeral with FastEmbed BGE:
        db = chromadb(in_memory=True, embedding="fastembed")

        # Online remote server with OpenAI embeddings:
        db = chromadb(host="my-chroma.internal", port=8000, embedding="openai")

        storage = vectorStorage(database=db)
        ```
    """
    return ChromaDB(
        path=path,
        host=host,
        port=port,
        ssl=ssl,
        headers=headers,
        in_memory=in_memory,
        collection_name=collection_name,
        embedding=embedding,
        embedding_model=embedding_model,
        embedding_function=embedding_function,
        **kwargs,
    )


__all__ = ["ChromaDB", "chromadb"]
