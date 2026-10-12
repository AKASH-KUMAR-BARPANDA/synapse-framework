"""Embedding model providers and resolution utilities for Synapse."""

from synapse.embeddings.base import (
    EmbeddingModelRegistry,
    fastembed,
    huggingface_embeddings,
    minilm,
    ollama_embeddings,
    openai_embeddings,
    resolve_embedding,
)

__all__ = [
    "EmbeddingModelRegistry",
    "fastembed",
    "huggingface_embeddings",
    "minilm",
    "ollama_embeddings",
    "openai_embeddings",
    "resolve_embedding",
]
