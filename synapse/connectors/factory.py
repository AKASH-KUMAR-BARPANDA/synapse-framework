"""Connector factory functions for dynamically constructing BaseConnector instances."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

from synapse.connectors.base import BaseConnector
from synapse.connectors.mcp_wrapper import MCPConnector


class FunctionalConnector(BaseConnector):
    """Dynamic BaseConnector implementation created by `make_connector`."""

    def __init__(
        self,
        name: str,
        service_manager: Any = None,
        server: Any = None,
        description: str = "",
        intent_regex: str | None = None,
        tools: dict[str, Callable[..., Any]] | None = None,
        default_tool: str = "",
        is_authenticated_fn: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(
            name=name,
            description=description or f"{name} custom connector",
            intent_regex=intent_regex,
            default_tool=default_tool,
        )
        self.service_manager = service_manager
        self.server = server
        self.tools_dict: dict[str, Callable[..., Any]] = tools or {}
        self.tools = self.tools_dict
        self.is_authenticated_fn = is_authenticated_fn

    def is_authenticated(self) -> bool:
        if self.is_authenticated_fn:
            try:
                return bool(self.is_authenticated_fn())
            except Exception:
                return False
        if self.service_manager and hasattr(
            self.service_manager, "is_authenticated"
        ):
            try:
                return bool(self.service_manager.is_authenticated())
            except Exception:
                return False
        return True

    async def list_tools(self) -> list[dict[str, Any]]:
        schemas: list[dict[str, Any]] = []
        for tool_name, func in self.tools_dict.items():
            doc = inspect.getdoc(func) or f"Execute {tool_name}."
            props: dict[str, Any] = {}
            required: list[str] = []
            try:
                sig = inspect.signature(func)
                for param_name, param in sig.parameters.items():
                    if param_name in ("self", "cls"):
                        continue
                    p_type = "string"
                    if param.annotation is int:
                        p_type = "integer"
                    elif param.annotation is float:
                        p_type = "number"
                    elif param.annotation is bool:
                        p_type = "boolean"
                    elif param.annotation is list:
                        p_type = "array"
                    elif param.annotation is dict:
                        p_type = "object"

                    prop_info: dict[str, Any] = {"type": p_type}
                    if param.default is inspect.Parameter.empty:
                        required.append(param_name)
                    else:
                        prop_info["default"] = param.default
                    props[param_name] = prop_info
            except Exception:
                pass  # nosec B110

            schema_obj: dict[str, Any] = {
                "type": "object",
                "properties": props,
            }
            if required:
                schema_obj["required"] = required

            schemas.append({
                "server": self.name,
                "name": tool_name,
                "description": doc,
                "inputSchema": schema_obj,
            })
        return schemas


    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        if tool_name not in self.tools_dict:
            raise KeyError(
                f"Tool '{tool_name}' not registered on connector '{self.name}'."
            )
        func = self.tools_dict[tool_name]
        args = arguments or {}
        if inspect.iscoroutinefunction(func):
            return await func(**args)
        return func(**args)


def make_connector(
    name: str,
    service_manager: Any = None,
    server: Any = None,
    description: str = "",
    intent_regex: str | None = None,
    tools: list[Callable[..., Any]] | dict[str, Callable[..., Any]] | None = None,
    default_tool: str = "",
    is_authenticated_fn: Callable[[], bool] | None = None,
) -> BaseConnector:
    """Creates a Synapse `BaseConnector` from custom service managers or servers.

    Args:
        name: Unique connector name.
        service_manager: Optional auth/service manager (e.g. GoogleOAuthService, NotionAuthService).
        server: Optional FastMCP server script path, server instance, or Stdio command.
        description: Description of the connector's capabilities.
        intent_regex: Optional regex string matching relevant user messages.
        tools: Optional dictionary or list of callable functions exposed as tools.
        default_tool: Optional default tool identifier.
        is_authenticated_fn: Optional custom readiness check callable.

    Returns:
        A ready-to-use `BaseConnector` instance.

    Example:
        ```python
        from synapse.connectors import make_connector

        def search_docs(query: str = ""):
            return [{"title": "Quickstart", "content": "..."}]

        docs_connector = make_connector(
            name="docs",
            description="Documentation search",
            tools={"search_docs": search_docs},
            default_tool="search_docs",
        )
        ```
    """
    # If server is a script path or command, wrap via MCPConnector
    if isinstance(server, (str, Path)) and (
        str(server).endswith(".py") or Path(server).exists()
    ):
        return MCPConnector(
            name=name,
            script_path=server,
            description=description,
            intent_regex=intent_regex,
            default_tool=default_tool,
            is_ready_fn=is_authenticated_fn,
        )

    # Normalize tools into a dictionary
    normalized_tools: dict[str, Callable[..., Any]] = {}
    if isinstance(tools, dict):
        normalized_tools = tools
    elif isinstance(tools, list):
        for fn in tools:
            fn_name = getattr(fn, "__name__", str(fn))
            normalized_tools[fn_name] = fn

    # Automatically extract tools from server if server has tools registry
    if server and hasattr(server, "_tools"):
        for t_name, t_fn in getattr(server, "_tools", {}).items():
            if t_name not in normalized_tools:
                normalized_tools[t_name] = t_fn

    chosen_default = default_tool or ""

    return FunctionalConnector(
        name=name,
        service_manager=service_manager,
        server=server,
        description=description,
        intent_regex=intent_regex,
        tools=normalized_tools,
        default_tool=chosen_default,
        is_authenticated_fn=is_authenticated_fn,
    )


# Developer-friendly alias matching user request
makeconnectors = make_connector
