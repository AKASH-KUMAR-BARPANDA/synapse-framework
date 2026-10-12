"""Abstract base interface for pluggable knowledge graph stores in Synapse."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseGraphStore(ABC):
    """Abstract interface that all Synapse knowledge graph backends must implement.

    Ensures interchangeability between NetworkX, in-memory graphs, Neo4j,
    or other graph databases.
    """

    @abstractmethod
    def add_node_entity(
        self,
        name: str,
        entity_type: str = "Default",
        color: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Adds or updates an entity node in the graph."""

    @abstractmethod
    def add_relation(
        self,
        source: str,
        relation: str,
        target: str,
        source_type: str = "Default",
        target_type: str = "Default",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Adds a directed relation edge between source and target entities."""

    def add_node(
        self,
        name: str,
        entity_type: str = "Default",
        color: str | None = None,
        attributes: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Convenience alias for add_node_entity."""
        attrs = dict(attributes or {})
        attrs.update(kwargs)
        self.add_node_entity(name=name, entity_type=entity_type, color=color, attributes=attrs)

    def add_edge(
        self,
        source: str,
        target_or_rel: str,
        target: str | None = None,
        relation: str = "CONNECTED_TO",
        source_type: str = "Default",
        target_type: str = "Default",
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Convenience alias for add_relation.

        Supports both:
          add_edge(u, v, relation="CONNECTED_TO")
          add_edge(u, "RELATION", v)
        """
        meta = dict(metadata or {})
        meta.update(kwargs)
        if target is not None:
            # 3 positional args: source, target_or_rel, target
            # e.g., add_edge("alice", "WORKS_AT", "synapse") -> relation="WORKS_AT", target="synapse"
            # or add_edge("alice", "synapse", "WORKS_AT") -> relation="WORKS_AT", target="synapse"
            if target_or_rel.isupper() and not target.isupper():
                actual_rel = target_or_rel
                actual_target = target
            else:
                actual_target = target_or_rel
                actual_rel = target
            self.add_relation(
                source=source,
                relation=actual_rel,
                target=actual_target,
                source_type=source_type,
                target_type=target_type,
                metadata=meta,
            )
        else:
            # 2 positional args: source, target
            self.add_relation(
                source=source,
                relation=relation,
                target=target_or_rel,
                source_type=source_type,
                target_type=target_type,
                metadata=meta,
            )


    @abstractmethod
    def find_relation_for(self, entity: str) -> list[str]:
        """Finds all incoming and outgoing relational facts for a given entity."""

    @abstractmethod
    def get_3d_payload(self) -> dict[str, Any]:
        """Returns node and link data formatted for 3D force-directed visualization."""

    @abstractmethod
    def get_stats(self) -> dict[str, Any]:
        """Returns summary node and edge counts."""

    def count_nodes(self) -> int:
        """Returns the total number of nodes in the graph."""
        return int(self.get_stats().get("total_nodes", 0))

    def count_edges(self) -> int:
        """Returns the total number of edges in the graph."""
        return int(self.get_stats().get("total_edges", 0))

    def clear(self) -> None:
        """Clears all nodes and edges from the graph."""

    def load(self) -> None:
        """Loads state from persistent storage if applicable."""

    def save(self) -> None:
        """Persists state to storage if applicable."""


__all__ = ["BaseGraphStore"]
