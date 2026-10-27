"""Abstract base class for all Synapse connectors."""

from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.documents import Document


class BaseConnector(ABC):
    """Abstract interface for all Synapse external connectors.

    Every connector exposes tools, authentication state checks, intent matching,
    and automatic indexing logic into ChromaDB and NetworkX.

    Attributes:
        name: Unique logical connector identifier (e.g. 'gmail', 'notion', 'photos').
        description: Human-readable summary of the connector's domain.
        intent_regex: Optional regex string used as a first-stage intent gate.
        default_tool: Default tool invoked during sync or fallback operations.
    """

    def __init__(
        self,
        name: str,
        description: str,
        intent_regex: str | None = None,
        default_tool: str = "",
    ) -> None:
        """Initializes the base connector.

        Args:
            name: Connector identifier.
            description: Description of the connector data and capabilities.
            intent_regex: Optional regex string matching user prompts that require this connector.
            default_tool: Default tool name.
        """
        self.name = name
        self.description = description
        self.intent_regex = intent_regex
        self._compiled_regex = (
            re.compile(intent_regex, re.IGNORECASE) if intent_regex else None
        )
        self.default_tool = default_tool

    def matches_intent(self, user_message: str) -> bool:
        """Checks if a user message matches this connector's intent regex."""
        if not self._compiled_regex:
            return True
        return bool(self._compiled_regex.search(user_message or ""))

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Checks whether the connector has valid authentication credentials."""
        ...

    @abstractmethod
    async def list_tools(self) -> list[dict[str, Any]]:
        """Returns the list of tool schemas exposed by this connector."""
        ...

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Executes a named tool with arguments.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments dictionary.

        Returns:
            Raw tool execution output (list of records or dictionary).
        """
        ...

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Executes a named tool (convenience alias for call_tool)."""
        return await self.call_tool(tool_name=tool_name, arguments=arguments)

    def default_args_builder(self, user_message: str) -> dict[str, Any]:
        """Builds default tool arguments from user prompt when arguments are missing."""
        return {}

    def chunk_record(
        self,
        tool_name: str,
        record: dict[str, Any],
    ) -> list[Document]:
        """Standardized chunking normalizer for records produced by this connector.

        Subclasses may override this method for specialized domain chunking.
        """
        rec_id = str(
            record.get("id")
            or record.get("url")
            or hashlib.sha256(str(record).encode("utf-8")).hexdigest()[:12]
        )
        title = str(
            record.get("title")
            or record.get("subject")
            or record.get("name")
            or f"{self.name.upper()} Record"
        ).strip()
        author = str(
            record.get("sender")
            or record.get("from")
            or record.get("author")
            or self.name
        ).strip()
        date_str = str(
            record.get("date")
            or record.get("created_at")
            or record.get("last_edited_time")
            or ""
        ).strip()
        body = str(
            record.get("body")
            or record.get("content")
            or record.get("text")
            or record.get("snippet")
            or ""
        ).strip()
        url = str(record.get("url") or "").strip()

        if not body and not title:
            return []

        header = f"[{self.name.upper()} | {tool_name}] Title: {title} | Source: {author}"
        if url:
            header += f" | URL: {url}"
        full_text = f"{header}\nDate: {date_str}\n\n{body}".strip()

        base_meta: dict[str, Any] = {
            "source": self.name,
            "tool": tool_name,
            "record_id": rec_id,
            "subject": title,
            "sender": author,
            "date": date_str,
            "url": url,
            "type": str(record.get("type") or self.name.capitalize()),
            "chunk_id": f"{self.name}:{rec_id}:0",
        }

        return [Document(page_content=full_text, metadata=base_meta)]

    def format_record(
        self,
        tool_name: str,
        record: dict[str, Any],
        index: int = 1,
    ) -> tuple[str, dict[str, Any], str]:
        """Formats a record for prompt context, UI RAG chunks, and knowledge graph triple.

        Returns:
            A tuple of (formatted_summary_line, live_chunk_dict, graph_triple_string).
        """
        title = str(
            record.get("title")
            or record.get("subject")
            or record.get("name")
            or record.get("action")
            or f"{self.name.upper()} #{index}"
        )
        author = str(
            record.get("sender")
            or record.get("author")
            or record.get("owner")
            or self.name.capitalize()
        )
        date_str = str(record.get("date") or "")
        body_excerpt = str(
            record.get("body")
            or record.get("content")
            or record.get("snippet")
            or record.get("message")
            or record.get("text")
            or record.get("details")
            or record.get("result")
            or (json.dumps(record, ensure_ascii=False) if record else "")
        )[:600].strip()
        entity_type = str(record.get("type") or "Topic").capitalize()

        summary_line = (
            f"{index}. [{self.name.upper()}] {title}\n"
            f"   Source: {author} | Date: {date_str}\n"
            f"   Content: {body_excerpt}"
        )

        live_chunk = {
            "page_content": (
                f"[{self.name.upper()} | {tool_name}] {title}\n"
                f"Date: {date_str}\n\n{body_excerpt}"
            ),
            "metadata": {
                "source": f"{self.name}_live",
                "subject": title,
                "sender": author,
                "date": date_str,
                "type": entity_type,
            },
            "source": f"{self.name}_live",
            "subject": title,
            "chunk_id": f"live_{self.name}_{record.get('id', index)}",
        }

        triple = f"{author} -> CONTAINS -> {title}"
        return summary_line, live_chunk, triple

    def to_mcp_server(self, name: str | None = None) -> Any:
        """Converts this connector into an official MCP Server instance."""
        from synapse.export.mcp_exporter import MCPExporter
        return MCPExporter.create_mcp_server(self, name=name or self.name)

    def run_mcp(self, transport: str = "stdio") -> None:
        """Runs this connector as a standalone MCP server over stdio or SSE."""
        server = self.to_mcp_server()
        server.run(transport=transport)

