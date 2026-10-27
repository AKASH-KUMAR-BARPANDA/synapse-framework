---
name: knowledge-graph
description: Entity extraction, relationship linking, multi-hop path reasoning, and knowledge graph construction.
tags: [knowledge-graph, entity-extraction, networkx, triples, reasoning]
tools: [synapse_graph_query, synapse_add_knowledge]
---

# Knowledge Graph Expert Skill

This skill governs entity recognition, relationship identification, and multi-hop graph reasoning over NetworkX and Neo4j stores.

## Operational Protocol
1. **Triple Extraction (Subject-Predicate-Object)**:
   - Identify discrete named entities: Person, Organization, Project, Tool, Topic, Location.
   - Extract semantic predicates in UPPER_SNAKE_CASE (e.g. `AUTHORED_BY`, `DEPENDS_ON`, `INTEGRATES_WITH`, `CONTAINS`).
2. **Multi-Hop Traversal**:
   - Trace relational paths between disconnected concepts (e.g., `A -> DEPENDS_ON -> B -> MAINTAINED_BY -> C`).
   - Identify shared neighbors and cluster hubs in the graph network.
3. **Graph Consistency**:
   - Deduplicate entity names (e.g., normalize aliases like `FastAPI` and `fastapi`).
   - Preserve temporal relations where dates and timestamps are present.
