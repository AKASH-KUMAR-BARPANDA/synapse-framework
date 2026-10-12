"""Pure in-memory vector database backend with zero disk dependencies."""

from __future__ import annotations

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
        self._entries: list[tuple[str, list[float], Document]] = []

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculates cosine similarity between two vector embeddings."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def add_documents(
        self,
        documents: list[Document],
        embeddings: list[list[float]] | None = None,
    ) -> list[str]:
        """Upserts documents into memory."""
        if not documents:
            return []

        texts = [doc.page_content for doc in documents]
        vecs = embeddings or self.embedding_function.embed_documents(texts)
        assigned_ids: list[str] = []

        for doc, vec in zip(documents, vecs):
            doc_id = str(doc.metadata.get("chunk_id") or uuid.uuid4())
            # Replace if same ID exists
            self._entries = [e for e in self._entries if e[0] != doc_id]
            self._entries.append((doc_id, vec, doc))
            assigned_ids.append(doc_id)

        return assigned_ids

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter_dict: dict[str, Any] | None = None,
        query_embedding: list[float] | None = None,
    ) -> list[Document]:
        """Performs nearest-neighbor search in RAM using cosine similarity."""
        if not self._entries:
            return []

        q_vec = query_embedding or self.embedding_function.embed_query(query)
        scored: list[tuple[float, Document]] = []

        for _, vec, doc in self._entries:
            # Check optional metadata filter
            if filter_dict:
                match = all(
                    doc.metadata.get(kf) == vf for kf, vf in filter_dict.items()
                )
                if not match:
                    continue

            score = self._cosine_similarity(q_vec, vec)
            scored.append((score, doc))

        # Sort descending by cosine similarity score
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:k]]

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
