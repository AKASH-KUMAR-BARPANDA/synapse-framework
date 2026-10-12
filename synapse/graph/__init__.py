"""Pluggable knowledge graph backends for Synapse."""

from synapse.graph.base import BaseGraphStore
from synapse.graph.memory import InMemoryGraph, in_memory_graph
from synapse.graph.neo4j_store import Neo4jGraph, neo4j
from synapse.graph.networkx_store import PALETTE, NetworkXGraph, networkx

# Backwards compatible alias
PersistentGraphStore = NetworkXGraph

__all__ = [
    "PALETTE",
    "BaseGraphStore",
    "InMemoryGraph",
    "Neo4jGraph",
    "NetworkXGraph",
    "PersistentGraphStore",
    "in_memory_graph",
    "neo4j",
    "networkx",
]
