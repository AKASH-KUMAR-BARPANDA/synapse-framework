"""Pure in-memory vector database backend with zero disk dependencies."""

from __future__ import annotations

import heapq
import math
import uuid
from typing import Any, Union

from langchain_core.documents import Document

from synapse.database.base import BaseVectorDB
from synapse.embeddings import resolve_embedding


class InMemoryDB(BaseVectorDB):
    """Pure in-memory vector database using cosine similarity in RAM."""

    def __init__(
        self,
        embedding: Union[str, Any] | None = None,
        embedding_model: str | None = None,
        embedding_function: Any | None = None,
        **kwargs: Any,
    ) -> None:
        """Initializes the in-memory vector database."""
        self.embedding_function = resolve_embedding(
            embedding=embedding or embedding_function or embedding_model,
            **kwargs,
        )
        # Store as dict {doc_id: (vec, doc, norm_vec)} for O(1) upserts and fast lookups
        self._entries: dict[str, tuple[list[float], Document, float]] = {}

    def _cosine_similarity(self, a: list[float], b: list[float], norm_a: float, norm_b: float) -> float:
        """Calculates cosine similarity between two vector embeddings."""
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        return dot / (norm_a * norm_b)

    def add_documents(
        self,
        documents: list[Document],
        embeddings: list[list[float]] | None = None,
    ) -> list[str]:
        """Upserts documents into memory with O(1) dict operations."""
        if not documents:
            return []

        texts = [doc.page_content for doc in documents]
        vecs = embeddings or self.embedding_function.embed_documents(texts)
        assigned_ids: list[str] = []

        for doc, vec in zip(documents, vecs):
            doc_id = str(doc.metadata.get("chunk_id") or uuid.uuid4())
            vec_norm = math.sqrt(sum(y * y for y in vec))
            self._entries[doc_id] = (vec, doc, vec_norm)
            assigned_ids.append(doc_id)

        return assigned_ids

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter_dict: dict[str, Any] | None = None,
        query_embedding: list[float] | None = None,
    ) -> list[Document]:
        """Performs nearest-neighbor search in RAM using cosine similarity and min-heap."""
        if not self._entries:
            return []

        q_vec = query_embedding or self.embedding_function.embed_query(query)
        q_norm = math.sqrt(sum(x * x for x in q_vec))
        if q_norm == 0.0:
            return []

        scored: list[tuple[float, Document]] = []

        for vec, doc, vec_norm in self._entries.values():
            # Check optional metadata filter
            if filter_dict:
                match = all(
                    doc.metadata.get(kf) == vf for kf, vf in filter_dict.items()
                )
                if not match:
                    continue

            score = self._cosine_similarity(q_vec, vec, q_norm, vec_norm)
            scored.append((score, doc))

        if not scored:
            return []

        top_matches = heapq.nlargest(k, scored, key=lambda x: x[0])
        return [doc for _, doc in top_matches]

    def count(self) -> int:
        """Returns the number of documents stored in RAM."""
        return len(self._entries)

    def clear(self) -> None:
        """Clears all in-memory entries."""
        self._entries.clear()


def in_memory(
    embedding: Union[str, Any] | None = None,
    embedding_model: str | None = None,
    embedding_function: Any | None = None,
    **kwargs: Any,
) -> InMemoryDB:
    """Factory helper creating an ephemeral in-memory vector database.

    Example:
        ```python
        from synapse.database import in_memory
        from synapse.storage import vectorStorage

        # In-memory with MiniLM:
        db = in_memory(embedding="minilm")

        # In-memory with FastEmbed BGE:
        db = in_memory(embedding="fastembed")

        storage = vectorStorage(database=db)
        ```
    """
    return InMemoryDB(
        embedding=embedding,
        embedding_model=embedding_model,
        embedding_function=embedding_function,
        **kwargs,
    )


__all__ = ["InMemoryDB", "in_memory"]
