"""NetworkX knowledge graph implementation for Synapse."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from synapse.config import DESIGN_TOKENS
from synapse.graph.base import BaseGraphStore

PALETTE: dict[str, str] = DESIGN_TOKENS["palettes"]["zinc"]


class NetworkXGraph(BaseGraphStore):
    """NetworkX directed knowledge graph supporting file persistence or ephemeral RAM."""

    def __init__(
        self,
        filepath: str | Path | None = None,
        palette: dict[str, str] | None = None,
    ) -> None:
        """Initializes NetworkX knowledge graph.

        Args:
            filepath: Optional persistent JSON file path. If None, operates purely in RAM.
            palette: Optional dictionary mapping entity types to hex color strings.
        """
        self.filepath = Path(filepath).resolve() if filepath else None
        self.palette = palette or PALETTE
        self.graph: nx.DiGraph = nx.DiGraph()
        self._lower_node_map: dict[str, str] = {}
        if self.filepath:
            self.load()

    def add_node_entity(
        self,
        name: str,
        entity_type: str = "Default",
        color: str | None = None,
        attributes: dict[str, Any] | None = None,
        auto_save: bool = True,
    ) -> None:
        """Adds or updates an entity node in the graph."""
        clean_name = name.strip()
        if not clean_name:
            return

        assigned_color = color or self.palette.get(
            entity_type, self.palette.get("Default", "#71717a")
        )
        node_data: dict[str, Any] = {
            "name": clean_name,
            "type": entity_type,
            "color": assigned_color,
        }
        if attributes:
            node_data.update(attributes)

        if clean_name in self.graph:
            self.graph.nodes[clean_name].update(node_data)
        else:
            self.graph.add_node(clean_name, **node_data)
        self._lower_node_map[clean_name.lower()] = clean_name

        if auto_save:
            self.save()

    def add_relation(
        self,
        source: str,
        relation: str,
        target: str,
        source_type: str = "Default",
        target_type: str = "Default",
        metadata: dict[str, Any] | None = None,
        auto_save: bool = True,
    ) -> None:
        """Adds a directed relation edge between source and target entities."""
        s = source.strip()
        t = target.strip()
        r = relation.strip().upper().replace(" ", "_")

        if not s or not t:
            return

        self.add_node_entity(s, entity_type=source_type, auto_save=False)
        self.add_node_entity(t, entity_type=target_type, auto_save=False)

        edge_data: dict[str, Any] = {"relation": r}
        if metadata:
            edge_data.update(metadata)

        self.graph.add_edge(s, t, **edge_data)
        if auto_save:
            self.save()

    def add_relations(
        self,
        relations: list[dict[str, Any] | tuple[str, str, str]],
    ) -> None:
        """Batch-adds multiple relation triples with a single atomic disk save."""
        for item in relations:
            if isinstance(item, (tuple, list)) and len(item) >= 3:
                s, r, t = str(item[0]), str(item[1]), str(item[2])
                self.add_relation(s, r, t, auto_save=False)
            elif isinstance(item, dict):
                s = str(item.get("source", ""))
                r = str(item.get("relation", "CONNECTED_TO"))
                t = str(item.get("target", ""))
                st = str(item.get("source_type", "Default"))
                tt = str(item.get("target_type", "Default"))
                meta = item.get("metadata")
                self.add_relation(s, r, t, source_type=st, target_type=tt, metadata=meta, auto_save=False)
        self.save()

    def find_relation_for(self, entity: str) -> list[str]:
        """Finds all relational facts directly connected to an entity."""
        facts: list[str] = []
        clean = entity.strip()
        if clean not in self.graph:
            # O(1) case-insensitive lookup
            found = self._lower_node_map.get(clean.lower())
            if not found:
                return facts
            clean = str(found)

        # Outgoing edges
        for _, target, data in self.graph.out_edges(clean, data=True):
            rel = data.get("relation", "RELATION")
            facts.append(f"{clean} -> {rel} -> {target}")

        # Incoming edges
        for source, _, data in self.graph.in_edges(clean, data=True):
            rel = data.get("relation", "RELATION")
            facts.append(f"{source} -> {rel} -> {clean}")

        return facts

    def get_3d_payload(self) -> dict[str, Any]:
        """Serializes nodes and edges into 3D force-directed layout format."""
        nodes: list[dict[str, Any]] = []
        for node_id, data in self.graph.nodes(data=True):
            node_type = data.get("type", "Default")
            color = data.get("color", self.palette.get(node_type, "#71717a"))
            degree = self.graph.degree(node_id)
            val = max(3.5, min(14.0, degree * 2.2))
            nodes.append({
                "id": str(node_id),
                "name": str(node_id),
                "label": str(node_id),
                "type": node_type,
                "color": color,
                "degree": degree,
                "val": val,
                "metadata": data,
            })

        links: list[dict[str, Any]] = []
        for u, v, data in self.graph.edges(data=True):
            rel = data.get("relation", "RELATION")
            links.append({
                "source": str(u),
                "target": str(v),
                "relation": rel,
                "label": rel,
                "metadata": data,
            })

        return {"nodes": nodes, "links": links}

    def get_stats(self) -> dict[str, Any]:
        """Returns summary node and edge counts."""
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
        }

    def count_nodes(self) -> int:
        """Returns the total number of nodes in the graph."""
        return self.graph.number_of_nodes()

    def count_edges(self) -> int:
        """Returns the total number of edges in the graph."""
        return self.graph.number_of_edges()

    def clear(self) -> None:
        """Clears all nodes and edges from the graph."""
        self.graph.clear()
        self._lower_node_map.clear()
        self.save()

    def load(self) -> None:
        """Loads graph state from persistent JSON file if configured."""
        if not self.filepath or not self.filepath.exists():
            return
        try:
            content = self.filepath.read_text(encoding="utf-8")
            if not content.strip():
                return
            data = json.loads(content)
            self.graph = nx.node_link_graph(data, edges="links")
            self._lower_node_map = {str(n).lower(): str(n) for n in self.graph.nodes}
        except Exception:
            pass  # nosec B110

    def save(self) -> None:
        """Persists graph state to JSON file if configured."""
        if not self.filepath:
            return
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            payload = nx.node_link_data(self.graph, edges="links")
            self.filepath.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass  # nosec B110


def networkx(
    filepath: str | Path | None = None,
    palette: dict[str, str] | None = None,
) -> NetworkXGraph:
    """Factory helper creating a NetworkX knowledge graph.

    Args:
        filepath: Optional path to JSON persistence file. If None, runs purely in RAM.
        palette: Optional dictionary mapping entity types to colors.

    Example:
        ```python
        from synapse.graph import networkx

        # File-backed persistence:
        graph = networkx("data/graph.json")

        # In-memory ephemeral (zero disk files):
        graph = networkx()
        ```
    """
    return NetworkXGraph(filepath=filepath, palette=palette)


__all__ = ["PALETTE", "NetworkXGraph", "networkx"]
