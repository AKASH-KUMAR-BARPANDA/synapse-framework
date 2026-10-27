"""Hybrid vector and knowledge graph context retriever."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.documents import Document

from synapse.config import DEFAULT_TOP_K


class HybridRAGEngine:
    """Combines dense semantic similarity search with knowledge graph multi-hop relations."""

    def __init__(
        self,
        vector_store: Any | None = None,
        graph_store: Any | None = None,
    ) -> None:
        """Initializes the Hybrid RAG engine."""
        self.vector_store = vector_store
        self.graph_store = graph_store

    def _extract_candidate_entities(self, query: str) -> list[str]:
        candidates: set[str] = set()
        if self.graph_store and hasattr(self.graph_store, "graph") and hasattr(self.graph_store.graph, "nodes"):
            query_lower = query.lower()
            nodes = self.graph_store.graph.nodes
            num_nodes = len(nodes)
            if num_nodes <= 100:
                for node in nodes:
                    if str(node).lower() in query_lower:
                        candidates.add(str(node))
            else:
                # Optimized O(M) n-gram token lookup for large graphs
                node_map = {str(n).lower(): str(n) for n in nodes}
                tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", query_lower)
                # Check 1-grams, 2-grams, 3-grams
                for n_gram_size in range(1, 4):
                    for i in range(len(tokens) - n_gram_size + 1):
                        gram = " ".join(tokens[i : i + n_gram_size])
                        if gram in node_map:
                            candidates.add(node_map[gram])

        matches = re.findall(r"\b[A-Z][a-zA-Z0-9_-]+\b", query)
        for match in matches:
            candidates.add(match)

        return list(candidates)

    def retrieve_context(
        self,
        query: str,
        k: int = DEFAULT_TOP_K,
        filter_dict: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Retrieves matching vector chunks and relational facts for a query."""
        vector_docs: list[Document] = []
        if self.vector_store is not None:
            try:
                vector_docs = self.vector_store.similarity_search(
                    query=query, k=k, filter_dict=filter_dict
                )
            except Exception:
                vector_docs = []

        candidate_entities: list[str] = []
        graph_facts: list[str] = []
        if self.graph_store is not None:
            try:
                candidate_entities = self._extract_candidate_entities(query)
                for entity in candidate_entities:
                    facts = self.graph_store.find_relation_for(entity)
                    graph_facts.extend(facts)
            except Exception:
                pass  # nosec B110

        unique_facts = list(dict.fromkeys(graph_facts))
        formatted_context = self._format_prompt_context(
            vector_docs, unique_facts
        )

        serialized_chunks = [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata,
                "source": doc.metadata.get("source", "chroma_db"),
                "subject": doc.metadata.get("subject", ""),
                "chunk_id": doc.metadata.get("chunk_id", ""),
            }
            for doc in vector_docs
        ]

        return {
            "query": query,
            "vector_documents": vector_docs,
            "chunks": serialized_chunks,
            "graph_facts": unique_facts,
            "graph_triples": unique_facts,
            "entities_detected": candidate_entities,
            "formatted_context": formatted_context,
        }

    @staticmethod
    def _format_prompt_context(
        vector_docs: list[Document],
        graph_facts: list[str],
    ) -> str:
        sections: list[str] = []

        if graph_facts:
            facts_block = "\n".join(f"- {fact}" for fact in graph_facts)
            sections.append(
                f"### RELATIONAL KNOWLEDGE GRAPH FACTS:\n{facts_block}"
            )

        if vector_docs:
            doc_chunks: list[str] = []
            for idx, doc in enumerate(vector_docs, 1):
                src = doc.metadata.get("source", "unknown")
                subj = doc.metadata.get("subject", "")
                header = f"[{src.upper()}" + (f" - {subj}" if subj else "") + "]"
                doc_chunks.append(
                    f"{idx}. {header}\n{doc.page_content.strip()}"
                )
            sections.append(
                "### RELEVANT DOCUMENT EXCERPTS:\n" + "\n\n".join(doc_chunks)
            )

        if not sections:
            return "No relevant past context or graph facts found."

        return "\n\n".join(sections)
