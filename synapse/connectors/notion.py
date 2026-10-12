"""Notion connector for searching and indexing workspace documents."""

from __future__ import annotations

import re
from typing import Any

import httpx

from synapse.connectors.base import BaseConnector
from synapse.oauth.notion import NotionAuthService


class NotionConnector(BaseConnector):
    """Notion workspace connector for querying pages, databases, and notes.

    Attributes:
        auth: NotionAuthService managing API authentication headers.
    """

    def __init__(
        self,
        api_key: str | None = None,
        auth_service: NotionAuthService | None = None,
    ) -> None:
        """Initializes the NotionConnector.

        Args:
            api_key: Optional Notion API integration token.
            auth_service: Optional pre-configured NotionAuthService instance.
        """
        super().__init__(
            name="notion",
            description="Notion workspace pages, notes, wiki docs, and databases",
            intent_regex=(
                r"\b(notion|wiki|workspace\s+page|workspace\s+pages|notion\s+page|"
                r"notion\s+pages|notion\s+note|notion\s+notes|notion\s+database)\b"
            ),
            default_tool="search_notion_pages",
        )
        self.auth = auth_service or NotionAuthService(api_key=api_key)

    def is_authenticated(self) -> bool:
        """Checks if a Notion API token is available."""
        return self.auth.is_authenticated()

    async def list_tools(self) -> list[dict[str, Any]]:
        """Returns the Notion tool schemas."""
        return [
            {
                "server": self.name,
                "name": "search_notion_pages",
                "description": "Search Notion workspace pages and databases matching a query.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "default": "",
                            "description": "Title or keyword substring to search.",
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 5,
                            "description": "Maximum number of Notion items to return.",
                        },
                    },
                },
            }
        ]

    def default_args_builder(self, user_message: str) -> dict[str, Any]:
        """Strips conversational noise from user prompt for Notion search."""
        text = (user_message or "").strip()
        cleaned = re.sub(
            r"\b(check|find|search|show|my|in|on|from|notion|pages|page|notes|note|database|workspace|docs)\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        cleaned = " ".join(cleaned.split()).strip("?.!,")
        return {"query": cleaned[:80], "max_results": 5}

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Executes a Notion tool."""
        args = arguments or {}
        if tool_name == "search_notion_pages":
            query = str(args.get("query", ""))
            max_results = int(args.get("max_results", 5))
            return await self.search_notion_pages(
                query=query, max_results=max_results
            )
        raise ValueError(
            f"Unknown tool '{tool_name}' for connector '{self.name}'"
        )

    async def search_notion_pages(
        self,
        query: str = "",
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Executes a live search against the Notion v1 REST API."""
        if not self.is_authenticated():
            return []

        payload: dict[str, Any] = {"page_size": max(1, min(max_results, 20))}
        if query.strip():
            payload["query"] = query.strip()

        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(
                f"{self.auth.base_url}/search",
                headers=self.auth.get_headers(),
                json=payload,
            )
            res.raise_for_status()
            data = res.json()

        results: list[dict[str, Any]] = []
        for item in data.get("results", []):
            item_id = item.get("id", "")
            obj_type = item.get("object", "page")
            url = item.get("url", "")
            last_edited = item.get("last_edited_time", "")

            title = "Untitled Notion Page"
            props = item.get("properties", {})
            for prop_val in props.values():
                if (
                    isinstance(prop_val, dict)
                    and prop_val.get("type") == "title"
                ):
                    title_arr = prop_val.get("title", [])
                    if title_arr:
                        title = (
                            "".join(
                                t.get("plain_text", "") for t in title_arr
                            ).strip()
                            or title
                        )
                    break

            results.append({
                "id": item_id,
                "title": title,
                "type": obj_type,
                "url": url,
                "date": last_edited,
                "content": f"Notion {obj_type}: {title} (URL: {url})",
            })

        return results


# Developer-friendly aliases matching different casing
NotionConnectors = NotionConnector
NotionsConnector = NotionConnector
