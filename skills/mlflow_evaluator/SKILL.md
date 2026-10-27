---
name: mlflow-evaluator
description: Experiment tracking, RAG latency analysis, retrieval recall evaluation, and model metric logging with MLflow.
tags: [mlflow, evaluation, telemetry, rag-metrics, tracking]
tools: []
---

# MLflow Evaluator Skill

Governs experimental tracking, latency benchmarking, and RAG evaluation using the MLflow integration in Synapse.

## Operational Protocol
1. **Experiment Initialization**:
   - Assign clean experiment names (e.g. `synapse_rag_eval`, `hybrid_search_benchmark`).
   - Group related query evaluations under identifiable run names or session IDs.
2. **Metric Logging**:
   - Log latency metrics: `retrieval_latency_ms`, `tool_execution_latency_ms`, `generation_latency_ms`, `total_latency_ms`.
   - Log quality metrics: `chunks_retrieved_count`, `graph_facts_count`, `context_character_count`, `tokens_generated`.
3. **Parameter Tracking**:
   - Log hyperparameters: `model_name`, `temperature`, `chunk_size`, `chunk_overlap`, `top_k`, `use_rag`.
4. **Artifact Storage**:
   - Save exported 3D WebGL knowledge graph files (`graph.html`).
   - Save retrieved context JSON dumps for offline precision and recall auditing.
