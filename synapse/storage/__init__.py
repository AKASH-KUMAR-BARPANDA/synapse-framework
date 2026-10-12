"""Storage layer exports for vector and knowledge graph persistence."""

from synapse.storage.graph_exporter import GraphExporter
from synapse.storage.graph_store import PersistentGraphStore
from synapse.storage.vector_store import (
    LocalVectorStorage,
    LocalVectorStore,
    VectorStorage,
    vectorStorage,
)

KnowledgeGraphStore = PersistentGraphStore
VectorStore = VectorStorage

__all__ = [
    "GraphExporter",
    "KnowledgeGraphStore",
    "LocalVectorStorage",
    "LocalVectorStore",
    "PersistentGraphStore",
    "VectorStorage",
    "VectorStore",
    "vectorStorage",
]
