---
name: Synapse Framework
description: Modular Multi-MCP and Hybrid RAG application framework combining dense vector embeddings with semantic knowledge graphs and on-demand MCP tool calling.
tags: [mcp, rag, knowledge-graph, agents, ai-framework]
---

# Synapse AI Framework Skill

Synapse is a modular Python framework for building personal intelligence backends, Model Context Protocol (MCP) servers, and Hybrid RAG assistants.

## When to Use This Skill
- Orchestrating multi-MCP servers (Gmail, Notion, Google Photos, Filesystem, Custom APIs).
- Performing hybrid dense vector search combined with multi-hop knowledge graph traversal.
- Deploying AI backends with FastAPI, Server-Sent Events (SSE) streaming, and interactive 3D WebGL inspector dashboards.
- Tracking experiments, latency, and retrieval quality with MLflow.

## Core Architecture Patterns
1. **Hybrid RAG**: Always query both semantic vector chunks (`VectorStorage`) and relational graph facts (`BaseGraphStore`). Cross-verify entity claims between graph triples and vector text.
2. **On-Demand MCP Tool Calling**: Only execute connector tools when the user's intent specifically warrants external action or fresh data fetching.
3. **Skill & Prompt Execution**: Expose domain workflows as reusable skills and callable MCP Prompts.
4. **Clean Stdio Communication**: When running as an MCP server, stdout is strictly reserved for JSON-RPC frames. Background logs and warnings route to stderr.
