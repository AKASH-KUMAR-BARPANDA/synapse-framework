---
name: mcp-orchestrator
description: Dynamic Model Context Protocol (MCP) server routing, tool call orchestration, and execution safety.
tags: [mcp, tool-calling, orchestrator, stdio, multi-server]
tools: [gmail_search_emails, notion_search_notion_pages]
---

# MCP Orchestrator Skill

Governs tool discovery, schema validation, and secure execution across multiple Model Context Protocol (MCP) servers.

## Operational Protocol
1. **Tool Intent Gating**: Match user prompts against connector intent patterns. Never call tools unnecessarily for pure conversational turns.
2. **Argument Construction**: Build schema-compliant JSON payloads for tool invocations. Coerce types according to inputSchema requirements.
3. **Execution Safety**:
   - Handle tool execution errors gracefully without breaking the stream.
   - Truncate excessively large tool responses before inserting them into the LLM context window.
   - Log tool execution latency and record counts.
4. **Context Injection**: Format raw tool records into clean markdown summaries and extract semantic triples to enrich the persistent graph.
