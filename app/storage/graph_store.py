import json
import os
from typing import List, Dict, Any, Optional
import networkx as nx

from app.config import GRAPH_FILE

PALETTE = {
    "Person": "#a78bfa",    # Soft Purple
    "Email": "#38bdf8",     # Cyan
    "Project": "#34d399",   # Emerald Green
    "Topic": "#f472b6",     # Rose Pink
    "Tool": "#fbbf24",      # Amber Yellow
    "Default": "#94a3b8"
}


class PersistentGraphStore:
    def __init__(self, filepath=GRAPH_FILE):
        self.filepath = filepath
        self.graph = nx.DiGraph()
        self.load()

    def add_node_entity(
        self,
        name: str,
        entity_type: str = 'Default',
        color: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        clean_name = name.strip()
        if not clean_name:
            return

        assigned_color = color or PALETTE.get(entity_type, PALETTE['Default'])
        node_data = {
            'name': clean_name,
            'type': entity_type,
            'color': assigned_color
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
        source_type: str = 'Default',
        target_type: str = 'Default',
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        clean_source = source.strip()
        clean_target = target.strip()
        clean_rel = relation.strip().upper()

        if not clean_source or not clean_target:
            return

        if not self.graph.has_node(clean_source):
            self.add_node_entity(clean_source, entity_type=source_type)

        if not self.graph.has_node(clean_target):
            self.add_node_entity(clean_target, entity_type=target_type)

        edge_data = {'relation': clean_rel}
        if metadata:
            edge_data.update(metadata)

        self.graph.add_edge(clean_source, clean_target, **edge_data)
        self.save()

    def find_relation_for(self, entity_name: str) -> List[str]:
        clean_entity = entity_name.strip()
        facts = []

        if not self.graph.has_node(clean_entity):
            return facts

        for neighbor in self.graph.successors(clean_entity):
            edge_data = self.graph.get_edge_data(clean_entity, neighbor) or {}
            rel = edge_data.get('relation', 'CONNECTED_TO')
            facts.append(f"{clean_entity} -> {rel} -> {neighbor}")

        for neighbor in self.graph.predecessors(clean_entity):
            edge_data = self.graph.get_edge_data(neighbor, clean_entity) or {}
            rel = edge_data.get('relation', 'CONNECTED_TO')
            facts.append(f"{neighbor} -> {rel} -> {clean_entity}")

        return facts

    def get_3d_payload(self) -> Dict[str, Any]:
        nodes = []
        for node_id, data in self.graph.nodes(data=True):
            node_type = data.get('type', 'Default')
            color = data.get('color', PALETTE.get(node_type, PALETTE['Default']))

            degree = self.graph.degree(node_id)
            node_size = max(3, min(14, degree * 2))

            nodes.append({
                "id": str(node_id),
                "name": str(node_id),
                "type": node_type,
                "color": color,
                "val": node_size,
                "attributes": {k: v for k, v in data.items() if k not in ["type", "color", "name"]}
            })

        links = []
        for u, v, data in self.graph.edges(data=True):
            links.append({
                'source': str(u),
                'target': str(v),
                'relation': data.get('relation', 'CONNECTED_TO')
            })

        return {'nodes': nodes, 'links': links}

    def load(self) -> None:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    if 'edges' in data and 'links' not in data:
                        data['links'] = data.pop('edges')

                    self.graph = nx.node_link_graph(data, directed=True)
            except Exception:
                self.graph = nx.DiGraph()

    def save(self) -> None:
        data = nx.node_link_data(self.graph)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def get_stats(self) -> Dict[str, int|float]:
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges()
        }