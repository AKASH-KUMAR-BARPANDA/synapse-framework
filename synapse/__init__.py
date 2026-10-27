"""Synapse — Modular Multi-MCP & Hybrid RAG Application Framework.

Clean, modular package organization:
- `from synapse import BaseApp`
- `from synapse.connectors import makeconnectors, GmailConnector, NotionConnector, ...`
- `from synapse.models import ollama, gemini, openai, OllamaModel, ...`
- `from synapse.database import chromadb, in_memory, qdrant, ChromaDB, ...`
- `from synapse.embeddings import fastembed, minilm, resolve_embedding, ...`
- `from synapse.graph import networkx, neo4j, NetworkXGraph, ...`
- `from synapse.skills import makeskills, Skill, load_premade_skill, ...`
- `from synapse.resource import Resource`
- `from synapse.storage import vectorStorage, VectorStorage`
- `from synapse.telemetry import MLflowTracker, track_run`
- `from synapse.export import MCPExporter, GraphExporter`
- `from synapse.oauth import GoogleOAuthService, NotionAuthService`
- `from synapse.rag import HybridRAGEngine, DocumentChunker`
"""

from __future__ import annotations

from synapse import connectors
from synapse import database
from synapse import embeddings
from synapse import export
from synapse import graph
from synapse import models
from synapse import oauth
from synapse import rag
from synapse import resource
from synapse import skills
from synapse import storage
from synapse import telemetry
from synapse import telemetry as mlflow
from synapse.app import BaseApp, SynapseApp

__version__ = "0.2.5"

__all__ = [
    "BaseApp",
    "SynapseApp",
    "__version__",
    "connectors",
    "database",
    "embeddings",
    "export",
    "graph",
    "mlflow",
    "models",
    "oauth",
    "rag",
    "resource",
    "skills",
    "storage",
    "telemetry",
]
