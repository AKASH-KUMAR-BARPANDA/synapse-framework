"""PostgreSQL PGVector database provider for Synapse."""

from __future__ import annotations

from typing import Any, Union

from langchain_core.documents import Document

from synapse.database.base import BaseVectorDB
from synapse.embeddings import resolve_embedding


class PGVectorDB(BaseVectorDB):
    """PostgreSQL pgvector database adapter for enterprise deployments."""

    def __init__(
        self,
        connection_string: str,
        collection_name: str = "synapse_embeddings",
        embedding: Union[str, Any] | None = None,
        embedding_model: str | None = None,
        embedding_function: Any | None = None,
        **kwargs: Any,
    ) -> None:
        self.connection_string = connection_string
        self.collection_name = collection_name
        self.embedding_function = resolve_embedding(
            embedding=embedding or embedding_function or embedding_model,
            **kwargs,
        )

        try:
            from langchain_community.vectorstores import PGVector

            self.store = PGVector(
                connection_string=connection_string,
                collection_name=collection_name,
                embedding_function=self.embedding_function,
            )
        except ImportError:
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
            return self.store.similarity_search(query=query, k=k)
        return self._fallback.similarity_search(query=query, k=k, filter_dict=filter_dict)

    def count(self) -> int:
        if self.store:
            return 0
        return self._fallback.count()

    def clear(self) -> None:
        if self.store:
            pass
        else:
            self._fallback.clear()


def pgvector(
    connection_string: str,
    collection_name: str = "synapse_embeddings",
    embedding: Union[str, Any] | None = None,
    embedding_model: str | None = None,
    embedding_function: Any | None = None,
    **kwargs: Any,
) -> PGVectorDB:
    """Factory helper to configure a PostgreSQL PGVector database instance."""
    return PGVectorDB(
        connection_string=connection_string,
        collection_name=collection_name,
        embedding=embedding,
        embedding_model=embedding_model,
        embedding_function=embedding_function,
        **kwargs,
    )


__all__ = ["PGVectorDB", "pgvector"]
