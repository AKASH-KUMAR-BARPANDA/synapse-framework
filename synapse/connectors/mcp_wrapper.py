"""Generic FastMCP / stdio MCP connector wrapper for the Synapse framework."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from synapse.connectors.base import BaseConnector


class MCPConnector(BaseConnector):
    """Wraps an external FastMCP or stdio MCP server into a Synapse BaseConnector.

    Enables adding any MCP server (e.g. GitHub, Slack, Google Calendar, Postgres)
    with a single class instantiation.

    Attributes:
        server_params: StdioServerParameters used to run the MCP subprocess.
    """

    def __init__(
        self,
        name: str,
        script_path: str | Path | None = None,
        command: str | None = None,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        description: str = "",
        intent_regex: str | None = None,
        default_tool: str = "",
        is_ready_fn: Callable[[], bool] | None = None,
        static_tools: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initializes the generic MCP connector.

        Args:
            name: Connector identifier.
            script_path: Path to a Python MCP server script.
            command: Executable command override (e.g. 'uvx', 'npx').
            args: CLI arguments when using an external command.
            env: Extra environment variables.
            description: Domain description.
            intent_regex: Regex for matching relevant user prompts.
            default_tool: Default tool name.
            is_ready_fn: Callable returning True when authentication is ready.
            static_tools: Pre-declared tool schemas.
        """
        super().__init__(
            name=name,
            description=description or f"{name} MCP connector",
            intent_regex=intent_regex,
            default_tool=default_tool,
        )
        self.is_ready_fn = is_ready_fn or (lambda: True)
        self.static_tools = static_tools or []
        self._tools_cache: list[dict[str, Any]] | None = (
            static_tools if static_tools else None
        )

        merged_env = os.environ.copy()
        if script_path:
            script_abs = Path(script_path).resolve()
            python_path = f"{script_abs.parent}:{merged_env.get('PYTHONPATH', '')}"
            merged_env["PYTHONPATH"] = python_path
            exec_cmd = command or sys.executable
            exec_args = args if args is not None else [str(script_abs)]
        else:
            exec_cmd = command or sys.executable
            exec_args = args or []

        if env:
            merged_env.update(env)

        self.server_params = StdioServerParameters(
            command=exec_cmd,
            args=exec_args,
            env=merged_env,
        )

    def is_authenticated(self) -> bool:
        """Checks if the wrapped MCP server is configured and ready."""
        try:
            return bool(self.is_ready_fn())
        except Exception:
            return False

    async def list_tools(self) -> list[dict[str, Any]]:
        """Discovers tools exposed by the MCP server."""
        if self._tools_cache:
            return self._tools_cache

        try:
            async with stdio_client(self.server_params) as (
                read_stream,
                write_stream,
            ), ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                discovered = [
                    {
                        "server": self.name,
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": getattr(
                            tool,
                            "inputSchema",
                            getattr(tool, "input_schema", {}),
                        ),
                    }
                    for tool in tools_result.tools
                ]
                self._tools_cache = discovered
                return discovered
        except Exception:
            return self.static_tools

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Invokes a tool on the MCP server over stdio."""
        async with stdio_client(self.server_params) as (
            read_stream,
            write_stream,
        ), ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                name=tool_name,
                arguments=arguments or {},
            )

            extracted_data: list[Any] = []
            for content in result.content:
                if hasattr(content, "text"):
                    try:
                        parsed = json.loads(content.text)
                        extracted_data.append(parsed)
                    except (json.JSONDecodeError, TypeError):
                        extracted_data.append(content.text)
                else:
                    extracted_data.append(content)

            if len(extracted_data) == 1:
                return extracted_data[0]
            return extracted_data
