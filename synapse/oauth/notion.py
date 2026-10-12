"""Notion API authentication and header manager."""

from __future__ import annotations

import os


class NotionAuthService:
    """Manages Notion REST API tokens and request headers.

    Attributes:
        api_key: Notion internal integration secret token.
        base_url: Base URL of the Notion v1 REST API.
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initializes the Notion authentication service.

        Args:
            api_key: Optional Notion API token (reads from NOTION_API_KEY env if omitted).
        """
        self.api_key = api_key or os.getenv("NOTION_API_KEY", "")
        self.base_url = "https://api.notion.com/v1"

    def is_authenticated(self) -> bool:
        """Checks if a non-empty API token is configured."""
        return bool(self.api_key and self.api_key.strip())

    def get_headers(self) -> dict[str, str]:
        """Constructs request headers for Notion API invocations."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
