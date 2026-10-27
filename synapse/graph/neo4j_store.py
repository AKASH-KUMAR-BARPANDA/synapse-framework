"""Neo4j graph database adapter for Synapse."""

from __future__ import annotations

from typing import Any

from synapse.config import DESIGN_TOKENS
from synapse.graph.base import BaseGraphStore


class Neo4jGraph(BaseGraphStore):
    """Neo4j graph database adapter connecting to enterprise or AuraDB clusters."""

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        auth: tuple[str, str] | Any | None = None,
        database: str = "neo4j",
        palette: dict[str, str] | None = None,
    ) -> None:
        self.uri = uri
        self.database = database
        self.palette = palette or DESIGN_TOKENS["palettes"]["zinc"]
        self.driver = None

        try:
            from neo4j import GraphDatabase

            self.driver = GraphDatabase.driver(uri, auth=auth)
        except ImportError:
            # Fallback in-memory representation if neo4j package is omitted
            from synapse.graph.memory import InMemoryGraph

            self._fallback = InMemoryGraph(palette=self.palette)

    def add_node_entity(
        self,
        name: str,
        entity_type: str = "Default",
        color: str | None = None,
        attributes: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if not self.driver:
            return self._fallback.add_node_entity(name, entity_type, color, attributes, **kwargs)

        assigned_color = color or self.palette.get(
            entity_type, self.palette.get("Default", "#71717a")
        )
        props = {"name": name, "type": entity_type, "color": assigned_color}
        if attributes:
            props.update(attributes)

        query = """
        MERGE (n:Entity {name: $name})
        SET n += $props
        """
        with self.driver.session(database=self.database) as session:
            session.run(query, name=name, props=props)

    def add_relation(
        self,
        source: str,
        relation: str,
        target: str,
        source_type: str = "Default",
        target_type: str = "Default",
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if not self.driver:
            return self._fallback.add_relation(
                source, relation, target, source_type, target_type, metadata, **kwargs
            )

        self.add_node_entity(source, entity_type=source_type)
        self.add_node_entity(target, entity_type=target_type)

        clean_rel = relation.strip().upper().replace(" ", "_")
        query = f"""
        MATCH (s:Entity {{name: $source}})
        MATCH (t:Entity {{name: $target}})
        MERGE (s)-[r:{clean_rel}]->(t)
        SET r += $props
        """
        with self.driver.session(database=self.database) as session:
            session.run(query, source=source, target=target, props=metadata or {})

    def find_relation_for(self, entity: str) -> list[str]:
        if not self.driver:
            return self._fallback.find_relation_for(entity)

        facts: list[str] = []
        query = """
        MATCH (s:Entity {name: $entity})-[r]->(t:Entity)
        RETURN s.name as source, type(r) as relation, t.name as target
        UNION
        MATCH (s:Entity)-[r]->(t:Entity {name: $entity})
        RETURN s.name as source, type(r) as relation, t.name as target
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, entity=entity)
            for record in result:
                facts.append(
                    f"{record['source']} -> {record['relation']} -> {record['target']}"
                )
        return facts

    def get_3d_payload(self) -> dict[str, Any]:
        if not self.driver:
            return self._fallback.get_3d_payload()

        nodes: list[dict[str, Any]] = []
        links: list[dict[str, Any]] = []

        query = """
        MATCH (s:Entity)-[r]->(t:Entity)
        RETURN s, r, t LIMIT 500
        """
        with self.driver.session(database=self.database) as session:
            res = session.run(query)
            seen_nodes = set()
            for record in res:
                s_node = record["s"]
                t_node = record["t"]
                r_rel = record["r"]

                for n in (s_node, t_node):
                    nid = n["name"]
                    if nid not in seen_nodes:
                        seen_nodes.add(nid)
                        ntype = n.get("type", "Default")
                        color = n.get("color", self.palette.get(ntype, "#71717a"))
                        nodes.append({
                            "id": nid,
                            "name": nid,
                            "label": nid,
                            "type": ntype,
                            "color": color,
                            "val": 5.0,
                        })

                links.append({
                    "source": s_node["name"],
                    "target": t_node["name"],
                    "relation": r_rel.type,
                    "label": r_rel.type,
                })

        return {"nodes": nodes, "links": links}

    def get_stats(self) -> dict[str, Any]:
        if not self.driver:
            return self._fallback.get_stats()

        query = """
        CALL { MATCH (n:Entity) RETURN count(n) as nodes }
        CALL { MATCH ()-[r]->() RETURN count(r) as edges }
        RETURN nodes, edges
        """
        with self.driver.session(database=self.database) as session:
            res = session.run(query).single()
            if res:
                return {"total_nodes": res["nodes"], "total_edges": res["edges"]}
        return {"total_nodes": 0, "total_edges": 0}


def neo4j(
    uri: str = "bolt://localhost:7687",
    auth: tuple[str, str] | Any | None = None,
    database: str = "neo4j",
    palette: dict[str, str] | None = None,
) -> Neo4jGraph:
    """Factory helper to configure a Neo4j graph database adapter."""
    return Neo4jGraph(uri=uri, auth=auth, database=database, palette=palette)


__all__ = ["Neo4jGraph", "neo4j"]
