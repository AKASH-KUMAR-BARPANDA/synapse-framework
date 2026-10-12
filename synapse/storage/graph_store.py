"""Persistent directed knowledge graph storage backed by NetworkX and JSON."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import networkx as nx

from synapse.config import DEFAULT_GRAPH_FILE, DESIGN_TOKENS
from synapse.graph.networkx_store import NetworkXGraph

PALETTE: dict[str, str] = DESIGN_TOKENS["palettes"]["zinc"]


class PersistentGraphStore(NetworkXGraph):
    """Manages a persistent directed graph of entities and relations."""

    def __init__(self, filepath: str | Path | None = None) -> None:
        """Initializes the graph store from a persistent JSON file."""
        super().__init__(filepath=filepath or DEFAULT_GRAPH_FILE)

    def add_node_entity(
        self,
        name: str,
        entity_type: str = "Default",
        color: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """Adds or updates an entity node in the graph."""
        clean_name = name.strip()
        if not clean_name:
            return

        assigned_color = color or self.palette.get(
            entity_type, self.palette["Default"]
        )
        node_data: dict[str, Any] = {
            "name": clean_name,
            "type": entity_type,
            "color": assigned_color,
        }
        if attributes:
            node_data.update(attributes)

        if self.graph.has_node(clean_name):
            self.graph.nodes[clean_name].update(node_data)
        else:
            self.graph.add_node(clean_name, **node_data)

        self.save()

    def add_relation(
        self,
        source: str,
        relation: str,
        target: str,
        source_type: str = "Default",
        target_type: str = "Default",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Creates a directed relation edge between source and target entities."""
        clean_source = source.strip()
        clean_target = target.strip()
        clean_rel = relation.strip().upper()

        if not clean_source or not clean_target:
            return

        if not self.graph.has_node(clean_source):
            self.add_node_entity(clean_source, entity_type=source_type)
        if not self.graph.has_node(clean_target):
            self.add_node_entity(clean_target, entity_type=target_type)

        edge_data: dict[str, Any] = {"relation": clean_rel}
        if metadata:
            edge_data.update(metadata)

        self.graph.add_edge(clean_source, clean_target, **edge_data)
        self.save()

    def find_relation_for(self, entity_name: str) -> list[str]:
        """Retrieves incoming and outgoing relational facts for an entity."""
        clean_entity = entity_name.strip()
        facts: list[str] = []

        if not self.graph.has_node(clean_entity):
            return facts

        for neighbor in self.graph.successors(clean_entity):
            edge_data = self.graph.get_edge_data(clean_entity, neighbor) or {}
            rel = edge_data.get("relation", "CONNECTED_TO")
            facts.append(f"{clean_entity} -> {rel} -> {neighbor}")

        for neighbor in self.graph.predecessors(clean_entity):
            edge_data = self.graph.get_edge_data(neighbor, clean_entity) or {}
            rel = edge_data.get("relation", "CONNECTED_TO")
            facts.append(f"{neighbor} -> {rel} -> {clean_entity}")

        return facts

    def get_3d_payload(self) -> dict[str, Any]:
        """Serializes the graph into 3D Force-Graph nodes and links."""
        nodes: list[dict[str, Any]] = []
        for node_id, data in self.graph.nodes(data=True):
            node_type = data.get("type", "Default")
            color = data.get(
                "color", self.palette.get(node_type, self.palette["Default"])
            )
            degree = self.graph.degree(node_id)
            node_size = max(3, min(14, degree * 2))

            nodes.append({
                "id": str(node_id),
                "name": str(node_id),
                "type": node_type,
                "color": color,
                "val": node_size,
                "attributes": {
                    k: v
                    for k, v in data.items()
                    if k not in ["type", "color", "name"]
                },
            })

        links: list[dict[str, Any]] = []
        for u, v, data in self.graph.edges(data=True):
            links.append({
                "source": str(u),
                "target": str(v),
                "relation": data.get("relation", "CONNECTED_TO"),
            })

        return {"nodes": nodes, "links": links}

    def load(self) -> None:
        """Loads graph data from JSON file on disk."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "edges" in data and "links" not in data:
                        data["links"] = data.pop("edges")
                    self.graph = nx.node_link_graph(data, directed=True)
            except Exception:
                self.graph = nx.DiGraph()

    def save(self) -> None:
        """Saves current graph to disk."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self.graph)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_stats(self) -> dict[str, int]:
        """Returns node and edge counts."""
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
        }
