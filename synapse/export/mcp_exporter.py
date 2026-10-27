"""MCP (Model Context Protocol) tool schema, server runner, and configuration exporter."""

from __future__ import annotations

import inspect
import json
import os
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    MCPServer = None  # type: ignore


class MCPExporter:
    """Exports Synapse connectors and tools to standard MCP schemas, client configs, and stdio servers."""

    @classmethod
    def to_tools_list(cls, source: Any) -> list[dict[str, Any]]:
        """Extracts standard MCP tool definitions from BaseApp or list of connectors."""
        connectors = cls._resolve_connectors(source)
        tools_list: list[dict[str, Any]] = []

        for conn in connectors:
            c_name = getattr(conn, "name", "custom_mcp")
            c_desc = getattr(conn, "description", "")
            raw_tools = (
                getattr(conn, "tools", None)
                or getattr(conn, "tools_dict", None)
                or {}
            )

            if isinstance(raw_tools, dict) and raw_tools:
                for t_name, t_func in raw_tools.items():
                    doc = getattr(t_func, "__doc__", "") or f"{t_name} tool provided by {c_name}"
                    tools_list.append({
                        "name": f"{c_name}_{t_name}" if c_name not in t_name else t_name,
                        "description": doc.strip(),
                        "server": c_name,
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search query or input parameter"}
                            },
                        },
                    })
            elif hasattr(conn, "default_tool") and conn.default_tool:
                tools_list.append({
                    "name": f"{c_name}_{conn.default_tool}",
                    "description": c_desc or f"Tool for {c_name}",
                    "server": c_name,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query or input parameter"}
                        },
                    },
                })

        return tools_list

    @classmethod
    def create_mcp_server(
        cls,
        source: Any,
        name: str | None = None,
    ) -> Any:
        """Instantiates an official `mcp.server.mcpserver.MCPServer` wired with connector tools, prompts, and resources."""
        if MCPServer is None:
            raise ImportError(
                "The 'mcp' package is required to create an MCP server. "
                "Install it with: pip install 'mcp>=2.3.0'"
            )

        server_name = name or getattr(source, "title", getattr(source, "name", "synapse"))
        server = MCPServer(name=server_name)

        # ---------------- 1. Register Connector Tools ----------------
        connectors = cls._resolve_connectors(source)
        for conn in connectors:
            c_name = getattr(conn, "name", "tool")
            raw_tools = (
                getattr(conn, "tools", None)
                or getattr(conn, "tools_dict", None)
                or {}
            )

            if isinstance(raw_tools, dict) and raw_tools:
                for t_name, t_func in raw_tools.items():
                    doc = getattr(t_func, "__doc__", "") or f"Execute {t_name} via {c_name}"
                    t_alias = f"{c_name}_{t_name}" if c_name not in t_name else t_name
                    server.add_tool(t_func, name=t_name, description=doc.strip())
                    if t_alias != t_name:
                        try:
                            server.add_tool(t_func, name=t_alias, description=doc.strip())
                        except Exception:
                            pass  # nosec B110
            elif hasattr(conn, "call_tool"):
                default_t = getattr(conn, "default_tool", "search")
                doc = getattr(conn, "description", f"Search {c_name}")

                def _make_adapter(c_instance: Any, t_action: str, doc_str: str) -> Callable[..., Any]:
                    async def dynamic_tool(query: str = "", max_results: int = 5) -> str:
                        args: dict[str, Any] = {"query": query, "max_results": max_results}
                        if inspect.iscoroutinefunction(c_instance.call_tool):
                            res = await c_instance.call_tool(t_action, args)
                        else:
                            res = c_instance.call_tool(t_action, args)
                        if isinstance(res, (dict, list)):
                            return json.dumps(res, indent=2)
                        return str(res)

                    dynamic_tool.__name__ = f"{c_instance.name}_{t_action}"
                    dynamic_tool.__doc__ = doc_str
                    return dynamic_tool

                adapter = _make_adapter(conn, default_t, doc)
                server.add_tool(adapter, name=f"{c_name}_{default_t}", description=doc)

        # ---------------- 2. Framework Core Tools ----------------
        if hasattr(source, "rag_engine") and source.rag_engine is not None:
            rag_ref = source.rag_engine

            async def synapse_rag_search(query: str, top_k: int = 4) -> str:
                """Retrieves relevant semantic document chunks and knowledge graph facts using Synapse Hybrid RAG."""
                ctx = rag_ref.retrieve_context(query, k=top_k)
                return ctx.get("formatted_context", "No relevant context found.")

            server.add_tool(
                synapse_rag_search,
                name="synapse_rag_search",
                description="Hybrid semantic RAG search across indexed documents and knowledge graph",
            )

        if hasattr(source, "graph_store") and source.graph_store is not None:
            graph_ref = source.graph_store

            async def synapse_graph_query(entity: str) -> str:
                """Queries semantic knowledge graph relations and relational facts connected to an entity."""
                facts = graph_ref.find_relation_for(entity)
                return "\n".join(facts) if facts else f"No relations found for '{entity}'."

            server.add_tool(
                synapse_graph_query,
                name="synapse_graph_query",
                description="Query relational knowledge graph facts and relations connected to an entity",
            )

        # ---------------- 3. Register MCP Prompts ----------------
        @server.prompt(
            name="rag_synthesis",
            description="Synthesize an answer using hybrid vector chunks and knowledge graph facts",
        )
        def prompt_rag_synthesis(query: str = "") -> str:
            return (
                f"You are an expert analyst. Research and answer the following question using "
                f"Synapse Hybrid RAG retrieval context and knowledge graph facts:\n\nQuestion: {query}"
            )

        @server.prompt(
            name="graph_reasoning",
            description="Explore multi-hop relationships and relational facts for an entity",
        )
        def prompt_graph_reasoning(entity: str = "") -> str:
            return (
                f"Explore multi-hop entity connections, relational triples, and cluster facts for "
                f"the entity '{entity}'. Formulate a structured knowledge synthesis."
            )

        @server.prompt(
            name="code_review",
            description="Review code changes for security, type safety, performance, and best practices",
        )
        def prompt_code_review(code: str = "") -> str:
            return (
                f"Perform a comprehensive code review focusing on: 1) Architecture, 2) Type Safety, "
                f"3) Security vulnerabilities, 4) Performance, and 5) PEP 8 clean code:\n\n```python\n{code}\n```"
            )

        @server.prompt(
            name="executive_summary",
            description="Extract bullet-pointed executive summaries with clear action items",
        )
        def prompt_executive_summary(content: str = "") -> str:
            return (
                f"Extract a structured executive summary with key takeaways and bullet points from:\n\n{content}"
            )

        # Wire loaded Skills as callable Prompts
        skills_list = []
        if hasattr(source, "list_skills"):
            skills_list = source.list_skills()
        elif hasattr(source, "_skills"):
            skills_list = source._skills
        else:
            try:
                from synapse.skills.skill import load_premade_skill
                skills_list = [
                    load_premade_skill("rag-analyst"),
                    load_premade_skill("knowledge-graph"),
                    load_premade_skill("mcp-orchestrator"),
                ]
            except Exception:
                pass  # nosec B110

        for sk in skills_list:
            clean_pname = re.sub(r"[^a-zA-Z0-9_]", "_", getattr(sk, "name", "skill").lower().strip())
            p_desc = getattr(sk, "description", "") or f"Agent Skill: {getattr(sk, 'name', 'skill')}"

            def _make_skill_prompt(skill_obj: Any) -> Callable[..., str]:
                def skill_prompt(context: str = "") -> str:
                    out = skill_obj.format_prompt()
                    if context.strip():
                        out += f"\n\nTask Context:\n{context.strip()}"
                    return out
                return skill_prompt

            try:
                server.prompt(name=clean_pname, description=p_desc)(_make_skill_prompt(sk))
            except Exception:
                pass  # nosec B110

        # ---------------- 4. Register MCP Resources ----------------
        @server.resource(
            "resource://synapse/knowledge_graph",
            name="knowledge_graph",
            description="Semantic knowledge graph entities and relations snapshot",
        )
        def res_knowledge_graph() -> str:
            if hasattr(source, "graph_store") and source.graph_store is not None:
                g = getattr(source.graph_store, "graph", None)
                if g is not None:
                    nodes = list(g.nodes)
                    edges = list(g.edges)
                    sample_rel = [f"{u} -> {g[u][v].get('relation', 'REL')} -> {v}" for u, v in edges[:25]]
                    return json.dumps({
                        "total_nodes": len(nodes),
                        "total_relations": len(edges),
                        "sample_entities": [str(n) for n in nodes[:25]],
                        "sample_relations": sample_rel,
                    }, indent=2)
            return json.dumps({"status": "no_graph_store_configured"}, indent=2)

        @server.resource(
            "resource://synapse/skills",
            name="synapse_skills",
            description="Catalog of loaded Synapse agent skills and guidelines",
        )
        def res_skills() -> str:
            catalog = [s.to_dict() if hasattr(s, "to_dict") else {"name": getattr(s, "name", str(s))} for s in skills_list]
            return json.dumps({"skills_count": len(catalog), "skills": catalog}, indent=2)

        @server.resource(
            "resource://synapse/status",
            name="system_status",
            description="Synapse system health, active model, and connectors",
        )
        def res_status() -> str:
            v_count = 0
            if hasattr(source, "vector_store") and source.vector_store:
                try:
                    v_count = source.vector_store.count()
                except Exception:
                    pass  # nosec B110
            status_info = {
                "title": getattr(source, "title", "Synapse"),
                "version": getattr(source, "version", "0.2.4"),
                "model": getattr(getattr(source, "model", None), "model_name", "unknown"),
                "connectors": [getattr(c, "name", str(c)) for c in cls._resolve_connectors(source)],
                "vector_chunks_indexed": v_count,
            }
            return json.dumps(status_info, indent=2)

        # Register custom Resource collections
        resources_list = getattr(source, "_resources", []) or []
        for r in resources_list:
            r_name = getattr(r, "name", "docs")
            uri = f"resource://synapse/resources/{r_name}"

            def _make_resource_fn(res_obj: Any) -> Callable[..., str]:
                def get_res_text() -> str:
                    docs = getattr(res_obj, "documents", [])
                    return "\n\n---\n\n".join(d.page_content for d in docs) if docs else "Empty resource collection."
                return get_res_text

            try:
                server.resource(uri, name=r_name, description=f"Resource collection '{r_name}'")(_make_resource_fn(r))
            except Exception:
                pass  # nosec B110

        return server

    @classmethod
    def run_stdio(
        cls,
        source: Any,
        name: str | None = None,
    ) -> None:
        """Runs the MCP server over standard I/O (stdio) for Claude Desktop, Cursor, or MCP validators."""
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        server = cls.create_mcp_server(source, name=name)
        server.run(transport="stdio")

    @classmethod
    def to_claude_desktop_config(
        cls,
        source: Any,
        server_name: str = "synapse",
        python_path: str | None = None,
        args: list[str] | None = None,
        host: str = "127.0.0.1",
        port: int = 8000,
    ) -> dict[str, Any]:
        """Generates standard claude_desktop_config.json configuration for Claude Desktop."""
        cmd = python_path or sys.executable or "python3"
        run_args = args or ["-m", "synapse.cli", "mcp"]
        return {
            "mcpServers": {
                server_name: {
                    "command": cmd,
                    "args": run_args,
                    "env": {
                        "SYNAPSE_HOST": host,
                        "SYNAPSE_PORT": str(port),
                    },
                }
            }
        }

    @classmethod
    def to_json(cls, source: Any, indent: int = 2) -> str:
        """Serializes all tool schemas and server definitions into a JSON string."""
        payload = {
            "mcpServers": cls.to_claude_desktop_config(source)["mcpServers"],
            "tools": cls.to_tools_list(source),
        }
        return json.dumps(payload, indent=indent)

    @classmethod
    def save_claude_desktop_config(
        cls,
        source: Any,
        filepath: str | Path = "claude_desktop_config.json",
        server_name: str = "synapse",
    ) -> Path:
        """Writes Claude Desktop configuration file to disk."""
        target = Path(filepath)
        target.parent.mkdir(parents=True, exist_ok=True)
        config = cls.to_claude_desktop_config(source, server_name=server_name)
        target.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return target

    @staticmethod
    def _resolve_connectors(source: Any) -> list[Any]:
        """Extracts connector objects from BaseApp, lists, or single connector instances."""
        if hasattr(source, "list_connectors"):
            return source.list_connectors()
        if hasattr(source, "_connectors"):
            return list(source._connectors.values())
        if isinstance(source, (list, tuple)):
            return list(source)
        if isinstance(source, dict):
            return list(source.values())
        if (
            hasattr(source, "call_tool")
            or hasattr(source, "tools_dict")
            or hasattr(source, "default_tool")
        ):
            return [source]
        return []


# Developer-friendly alias
mcpexporter = MCPExporter

__all__ = ["MCPExporter", "mcpexporter"]
