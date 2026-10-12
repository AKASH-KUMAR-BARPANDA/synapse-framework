"""Google Photos connector for the Synapse framework."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from synapse.connectors.base import BaseConnector
from synapse.oauth.google import GoogleOAuthService

PHOTOS_READONLY_SCOPE = (
    "https://www.googleapis.com/auth/photoslibrary.readonly"
)


class GooglePhotosConnector(BaseConnector):
    """Google Photos connector for searching and referencing photo media items.

    Attributes:
        oauth: Reusable GoogleOAuthService managing Google Photos scopes.
    """

    def __init__(
        self,
        credentials_path: str | Path = "credentials.json",
        token_path: str | Path = "token.json",  # nosec B107
        oauth_service: GoogleOAuthService | None = None,
        scopes: list[str] | None = None,
    ) -> None:
        """Initializes the GooglePhotosConnector.

        Args:
            credentials_path: Path to OAuth client secrets JSON.
            token_path: Path to cached token JSON.
            oauth_service: Optional pre-configured GoogleOAuthService instance.
            scopes: Optional list of OAuth scopes.
        """
        super().__init__(
            name="photos",
            description="Google Photos media library, photos, albums, and image metadata",
            intent_regex=(
                r"\b(photo|photos|image|images|picture|pictures|album|albums|"
                r"snapshot|snapshots|gallery|google\s+photos)\b"
            ),
            default_tool="search_photos",
        )

        active_scopes = list(scopes or [PHOTOS_READONLY_SCOPE])
        if oauth_service:
            self.oauth = oauth_service
            self.oauth.add_scopes(active_scopes)
        else:
            self.oauth = GoogleOAuthService(
                credentials_path=credentials_path,
                token_path=token_path,
                scopes=active_scopes,
            )

    def is_authenticated(self) -> bool:
        """Checks if a valid OAuth token exists for Google Photos."""
        return self.oauth.is_authenticated()

    async def list_tools(self) -> list[dict[str, Any]]:
        """Returns the Google Photos tool schemas."""
        return [
            {
                "server": self.name,
                "name": "search_photos",
                "description": "Search photos and media items in user's Google Photos library.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "default": "",
                            "description": "Optional search filter or category description.",
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 10,
                            "description": "Maximum number of photos to return.",
                        },
                    },
                },
            }
        ]

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Executes a Google Photos tool."""
        args = arguments or {}
        if tool_name == "search_photos":
            query = str(args.get("query", ""))
            max_results = int(args.get("max_results", 10))
            return self.search_photos(query=query, max_results=max_results)
        raise ValueError(
            f"Unknown tool '{tool_name}' for connector '{self.name}'"
        )

    def search_photos(
        self,
        query: str = "",
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Searches media items via Google Photos Library API."""
        if not self.is_authenticated():
            return []

        try:
            service = self.oauth.get_service(
                api_name="photoslibrary",
                version="v1",
                scopes=[PHOTOS_READONLY_SCOPE],
            )
            body: dict[str, Any] = {"pageSize": max(1, min(max_results, 50))}
            response = service.mediaItems().search(body=body).execute()
            items = response.get("mediaItems", [])

            results: list[dict[str, Any]] = []
            for item in items:
                results.append({
                    "id": item.get("id", ""),
                    "title": item.get("filename", "Photo"),
                    "url": item.get("productUrl", ""),
                    "mime_type": item.get("mimeType", ""),
                    "date": (
                        item.get("mediaMetadata", {}).get("creationTime", "")
                    ),
                    "description": item.get("description", ""),
                    "type": "Photo",
                })
            return results
        except Exception:
            return []


# Developer-friendly alias matching user request
GooglePhotosConnectors = GooglePhotosConnector
