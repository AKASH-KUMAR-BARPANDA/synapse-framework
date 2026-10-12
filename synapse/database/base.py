"""Abstract base interface for pluggable vector databases in Synapse."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.documents import Document


class BaseVectorDB(ABC):
    """Abstract interface that all Synapse vector database backends must implement.

    Ensures seamless interchangeability between local ChromaDB, in-memory storage,
    Qdrant, pgvector, or remote hosted vector databases.
    """

    @abstractmethod
    def add_documents(
        self,
        documents: list[Document],
        embeddings: list[list[float]] | None = None,
    ) -> list[str]:
        """Upserts a list of LangChain Document objects into the vector database.

        Args:
            documents: List of Document instances with page_content and metadata.
            embeddings: Optional precomputed vector embeddings.

        Returns:
            List of generated or assigned document ID strings.
        """

    @abstractmethod
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter_dict: dict[str, Any] | None = None,
        query_embedding: list[float] | None = None,
    ) -> list[Document]:
        """Performs semantic similarity search for a query string.

        Args:
            query: Natural language query string.
            k: Maximum number of nearest neighbors to return.
            filter_dict: Optional metadata filter dictionary.
            query_embedding: Optional precomputed query embedding vector.

        Returns:
            List of top-k closest Document instances.
        """

    @abstractmethod
    def count(self) -> int:
        """Returns the total number of document chunks currently indexed."""

    @abstractmethod
    def clear(self) -> None:
        """Clears all records in the collection/index."""


__all__ = ["BaseVectorDB"]
