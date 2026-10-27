---
name: rag-analyst
description: Deep context synthesis, factual citation grounding, and hybrid vector plus graph retrieval analysis.
tags: [rag, retrieval, context-synthesis, citations, analysis]
tools: [synapse_rag_search, synapse_graph_query]
---

# RAG Analyst Skill

The RAG Analyst skill specializes in extracting, cross-verifying, and synthesizing complex information from unstructured documents and semantic knowledge graphs.

## Operational Protocol
1. **Multi-Query Formulation**: Break down complex user questions into specific search keywords for dense vector retrieval and named entities for graph lookups.
2. **Context Cross-Verification**: Compare claims in vector chunks against relational facts in the knowledge graph:
   - If a vector chunk claims `Person X works at Company Y` and the graph triple confirms `Person X -> EMPLOYED_BY -> Company Y`, mark as high confidence.
   - If a discrepancy appears, highlight the conflict explicitly to the user.
3. **Citation & Source Attribution**: Always tag statements with their originating document subject, chunk ID, or connector source (e.g. `[README.md #chunk-3]`).
4. **Hallucination Prevention**: If retrieved context does not contain the answer, state clearly that information is not present in the indexed knowledge base rather than fabricating facts.
