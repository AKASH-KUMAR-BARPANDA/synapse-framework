"""MCP (Model Context Protocol) tool schema, server runner, and configuration exporter."""

from __future__ import annotations

import json
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
        """Instantiates an official `mcp.server.mcpserver.MCPServer` wired with connector tools."""
        if MCPServer is None:
            raise ImportError(
                "The 'mcp' package is required to create an MCP server. "
                "Install it with: pip install 'mcp>=2.3.0'"
            )

        server_name = name or getattr(source, "title", getattr(source, "name", "synapse"))
        server = MCPServer(name=server_name)

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
                    async def dynamic_tool(query: str = "", **kwargs: Any) -> str:
                        args = {"query": query, **kwargs} if query else kwargs
                        res = await c_instance.call_tool(t_action, args)
                        if isinstance(res, (dict, list)):
                            return json.dumps(res, indent=2)
                        return str(res)

                    dynamic_tool.__name__ = f"{c_instance.name}_{t_action}"
                    dynamic_tool.__doc__ = doc_str
                    return dynamic_tool

                adapter = _make_adapter(conn, default_t, doc)
                server.add_tool(adapter, name=f"{c_name}_{default_t}", description=doc)

        return server

    @classmethod
    def run_stdio(
        cls,
        source: Any,
        name: str | None = None,
    ) -> None:
        """Runs the MCP server over standard I/O (stdio) for Claude Desktop or Cursor."""
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
