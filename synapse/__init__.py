"""Synapse — Multi-MCP & Hybrid RAG Framework."""

from __future__ import annotations

import sys

from synapse import connectors as connectors
from synapse import database as database
from synapse import embeddings as embedding
from synapse import embeddings as embeddings
from synapse import export as export
from synapse import graph as graph
from synapse import models as model
from synapse import models as models
from synapse import oauth as Oauth
from synapse import oauth as oauth
from synapse import rag as rag
from synapse import resource as resource
from synapse import resource as resources
from synapse import skills as skills
from synapse import storage as storage
from synapse.app import BaseApp, SynapseApp
from synapse.connectors import (
    BaseConnector,
    GmailConnector,
    GmailConnectors,
    GooglePhotosConnector,
    GooglePhotosConnectors,
    MCPConnector,
    NotionConnector,
    NotionConnectors,
    NotionsConnector,
    make_connector,
    makeconnectors,
)
from synapse.database import (
    BaseVectorDB,
    ChromaDB,
    InMemoryDB,
    PGVectorDB,
    QdrantDB,
    chromadb,
    in_memory,
    pgvector,
    qdrant,
)
from synapse.embeddings import (
    fastembed,
    huggingface_embeddings,
    minilm,
    ollama_embeddings,
    openai_embeddings,
    resolve_embedding,
)
from synapse.export import (
    GraphExporter,
    MCPExporter,
    graphexporter,
    mcpexporter,
)
from synapse.graph import (
    BaseGraphStore,
    InMemoryGraph,
    Neo4jGraph,
    NetworkXGraph,
    in_memory_graph,
    neo4j,
    networkx,
)
from synapse.models import (
    BaseModelProvider,
    Gemimi,
    Gemini,
    GeminiModel,
    Ollama,
    OllamaModel,
    OpenAI,
    OpenAIModel,
    gemimi,
    gemini,
    get_model,
    ollama,
    openAI,
    openai,
)
from synapse.oauth import GoogleOAuthService, NotionAuthService
from synapse.rag import DocumentChunker, HybridRAGEngine
from synapse.resource import Resource
from synapse.skills import Skill, make_skill, makeskills
from synapse.storage import (
    LocalVectorStorage,
    LocalVectorStore,
    PersistentGraphStore,
    VectorStorage,
    vectorStorage,
)

__version__ = "0.2.4"

# Register module aliases in sys.modules
_this = sys.modules[__name__]
sys.modules["Synapse"] = _this
sys.modules["Synapse.app"] = sys.modules["synapse.app"]
sys.modules["Synapse.model"] = sys.modules["synapse.models"]
sys.modules["Synapse.models"] = sys.modules["synapse.models"]
sys.modules["synapse.model"] = sys.modules["synapse.models"]
sys.modules["Synapse.connectors"] = sys.modules["synapse.connectors"]
sys.modules["Synapse.database"] = sys.modules["synapse.database"]
sys.modules["Synapse.embeddings"] = sys.modules["synapse.embeddings"]
sys.modules["Synapse.embedding"] = sys.modules["synapse.embeddings"]
sys.modules["synapse.embedding"] = sys.modules["synapse.embeddings"]
sys.modules["Synapse.export"] = sys.modules["synapse.export"]
sys.modules["Synapse.exports"] = sys.modules["synapse.export"]
sys.modules["Synapse.graph"] = sys.modules["synapse.graph"]
sys.modules["Synapse.oauth"] = sys.modules["synapse.oauth"]
sys.modules["Synapse.Oauth"] = sys.modules["synapse.oauth"]
sys.modules["Synapse.storage"] = sys.modules["synapse.storage"]
sys.modules["Synapse.rag"] = sys.modules["synapse.rag"]
sys.modules["Synapse.skills"] = sys.modules["synapse.skills"]
sys.modules["Synapse.resource"] = sys.modules["synapse.resource"]
sys.modules["Synapse.resources"] = sys.modules["synapse.resource"]
sys.modules["synapse.resources"] = sys.modules["synapse.resource"]

__all__ = [
    "BaseApp",
    "BaseConnector",
    "BaseGraphStore",
    "BaseModelProvider",
    "BaseVectorDB",
    "ChromaDB",
    "DocumentChunker",
    "Gemimi",
    "Gemini",
    "GeminiModel",
    "GmailConnector",
    "GmailConnectors",
    "GoogleOAuthService",
    "GooglePhotosConnector",
    "GooglePhotosConnectors",
    "GraphExporter",
    "HybridRAGEngine",
    "InMemoryDB",
    "InMemoryGraph",
    "LocalVectorStorage",
    "LocalVectorStore",
    "MCPConnector",
    "MCPExporter",
    "Neo4jGraph",
    "NetworkXGraph",
    "NotionAuthService",
    "NotionConnector",
    "NotionConnectors",
    "NotionsConnector",
    "Oauth",
    "Ollama",
    "OllamaModel",
    "OpenAI",
    "OpenAIModel",
    "PGVectorDB",
    "PersistentGraphStore",
    "QdrantDB",
    "Resource",
    "Skill",
    "SynapseApp",
    "VectorStorage",
    "__version__",
    "chromadb",
    "connectors",
    "database",
    "embedding",
    "embeddings",
    "export",
    "fastembed",
    "gemimi",
    "gemini",
    "get_model",
    "graph",
    "graphexporter",
    "huggingface_embeddings",
    "in_memory",
    "in_memory_graph",
    "make_connector",
    "make_skill",
    "makeconnectors",
    "makeskills",
    "mcpexporter",
    "minilm",
    "model",
    "models",
    "neo4j",
    "networkx",
    "oauth",
    "ollama",
    "ollama_embeddings",
    "openAI",
    "openai",
    "openai_embeddings",
    "pgvector",
    "qdrant",
    "rag",
    "resolve_embedding",
    "resource",
    "resources",
    "skills",
    "storage",
    "vectorStorage",
]
