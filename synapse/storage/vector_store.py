"""Pluggable persistent and in-memory vector storage for Synapse."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from synapse.config import (
    DEFAULT_CHROMA_COLLECTION,
    DEFAULT_CHROMA_DIR,
)
from synapse.database.base import BaseVectorDB
from synapse.database.chroma import ChromaDB


class VectorStorage:
    """Universal vector storage container wrapping pluggable database backends.

    Example:
        ```python
        from synapse.database import chromadb, in_memory
        from synapse.storage import vectorStorage

        # With persistent ChromaDB:
        storage = vectorStorage(database=chromadb("data/chroma_db"))

        # With pure in-memory database:
        storage = vectorStorage(database=in_memory())

        # With remote online ChromaDB:
        storage = vectorStorage(database=chromadb(host="localhost", port=8000))
        ```
    """

    def __init__(
        self,
        database: BaseVectorDB | None = None,
        persist_dir: str | Path | None = None,
        collection_name: str = DEFAULT_CHROMA_COLLECTION,
        embedding: str | Any | None = None,
        embedding_model: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initializes the VectorStorage container.

        Args:
            database: Optional BaseVectorDB instance (e.g. chromadb(), in_memory(), qdrant()).
            persist_dir: Optional filesystem path for local ChromaDB if database not provided.
            collection_name: Collection name. Defaults to 'synapse_memory'.
            embedding: Embedding model name ('fastembed', 'minilm', 'openai', etc.) or Embeddings object.
            embedding_model: Backward-compatible alias for embedding model name.
            **kwargs: Extra database parameters.
        """
        if database is not None:
            self.database = database
        else:
            # Default to ChromaDB backend
            target_path = persist_dir or DEFAULT_CHROMA_DIR
            self.database = ChromaDB(
                path=target_path,
                collection_name=collection_name,
                embedding=embedding,
                embedding_model=embedding_model,
                **kwargs,
            )

    def add_documents(
        self,
        documents: list[Document | str],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Upserts documents into the underlying database."""
        docs_to_add: list[Document] = []
        for i, item in enumerate(documents):
            if isinstance(item, Document):
                docs_to_add.append(item)
            else:
                meta = metadatas[i] if metadatas and i < len(metadatas) else {}
                docs_to_add.append(Document(page_content=str(item), metadata=meta))
        return self.database.add_documents(docs_to_add)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[Document]:
        """Performs nearest-neighbor semantic search."""
        return self.database.similarity_search(query=query, k=k, filter_dict=filter_dict)

    def search(
        self,
        query: str,
        top_k: int = 4,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Convenience search helper returning dictionaries with page_content and metadata."""
        docs = self.similarity_search(query=query, k=top_k, filter_dict=filter_dict)
        return [
            {
                "page_content": d.page_content,
                "metadata": d.metadata,
                "source": d.metadata.get("source", ""),
                "score": getattr(d, "score", 0.0),
            }
            for d in docs
        ]

    def count(self) -> int:
        """Returns the total number of document chunks currently indexed."""
        return self.database.count()

    def clear(self) -> None:
        """Clears all indexed records."""
        self.database.clear()


# Developer-friendly alias matching user specification
vectorStorage = VectorStorage

# Backwards-compatible aliases
LocalVectorStore = VectorStorage
LocalVectorStorage = VectorStorage

__all__ = [
    "LocalVectorStorage",
    "LocalVectorStore",
    "VectorStorage",
    "vectorStorage",
]
