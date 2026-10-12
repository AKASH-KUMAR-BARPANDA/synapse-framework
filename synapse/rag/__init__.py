"""Retrieval-Augmented Generation (RAG) and chunking primitives."""

from synapse.rag.chunker import DocumentChunker
from synapse.rag.hybrid_rag import HybridRAGEngine

HybridRAG = HybridRAGEngine

__all__ = ["DocumentChunker", "HybridRAG", "HybridRAGEngine"]
