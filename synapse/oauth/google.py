"""Reusable Google OAuth 2.0 lifecycle and API service manager."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build


class GoogleOAuthService:
    """Manages Google OAuth 2.0 credentials, token refresh, and client discovery.

    Reusable across all Google-backed connectors (Gmail, Google Photos,
    Google Calendar, Google Drive).

    Attributes:
        credentials_path: Path to the Google Cloud OAuth 2.0 Client Secrets JSON.
        token_path: Path where authorized user tokens are stored.
        scopes: List of OAuth scope URIs required by the consumer connector(s).
    """

    def __init__(
        self,
        credentials_path: str | Path = "credentials.json",
        token_path: str | Path = "token.json",  # nosec B107
        scopes: list[str] | None = None,
    ) -> None:
        """Initializes the GoogleOAuthService.

        Args:
            credentials_path: Path to credentials.json. Defaults to 'credentials.json'.
            token_path: Path to token.json. Defaults to 'token.json'.
            scopes: Optional initial list of OAuth scope URIs.
        """
        self.credentials_path = Path(credentials_path).resolve()
        self.token_path = Path(token_path).resolve()
        self.scopes: list[str] = list(scopes or [])
        self._credentials: Credentials | None = None

    def add_scopes(self, scopes: list[str]) -> None:
        """Adds additional OAuth scopes to this service."""
        for s in scopes:
            if s not in self.scopes:
                self.scopes.append(s)

    def has_credentials(self) -> bool:
        """Checks if the client secrets credentials.json exists on disk."""
        return self.credentials_path.exists()

    def is_authenticated(self) -> bool:
        """Checks if a valid, non-expired token exists on disk or in memory."""
        if not self.token_path.exists():
            return False
        try:
            creds = Credentials.from_authorized_user_file(
                str(self.token_path), self.scopes or None
            )
            return bool(creds and (creds.valid or creds.refresh_token))
        except Exception:
            return False

    def authenticate(
        self, scopes: list[str] | None = None
    ) -> Credentials:
        """Loads, refreshes, or initiates a browser flow to acquire valid Credentials.

        Args:
            scopes: Optional override or extension of required OAuth scopes.

        Returns:
            A valid, active `google.oauth2.credentials.Credentials` instance.

        Raises:
            FileNotFoundError: If credentials_path is missing when authorization is needed.
        """
        active_scopes = list(scopes or self.scopes)

        if self.token_path.exists():
            try:
                self._credentials = Credentials.from_authorized_user_file(
                    str(self.token_path), active_scopes
                )
            except Exception:
                self._credentials = None

        if not self._credentials or not self._credentials.valid:
            if (
                self._credentials
                and self._credentials.expired
                and self._credentials.refresh_token
            ):
                self._credentials.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"Missing OAuth Client Secrets file at: '{self.credentials_path}'. "
                        "Please provide a valid credentials.json from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), active_scopes
                )
                self._credentials = flow.run_local_server(port=0)

            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, "w", encoding="utf-8") as f:
                f.write(self._credentials.to_json())

        return self._credentials

    def get_service(
        self,
        api_name: str,
        version: str,
        scopes: list[str] | None = None,
    ) -> Resource:
        """Builds an authenticated Google API Discovery Resource.

        Args:
            api_name: Google API name (e.g. 'gmail', 'photoslibrary').
            version: API version (e.g. 'v1').
            scopes: Required OAuth scopes.

        Returns:
            An authenticated Resource instance.
        """
        creds = self.authenticate(scopes)
        return build(api_name, version, credentials=creds)

    def save_credentials(self, content: str | bytes | dict[str, Any]) -> Path:
        """Validates and persists uploaded OAuth Client Secrets content to disk.

        Args:
            content: Raw JSON bytes, string, or parsed dictionary.

        Returns:
            Resolved Path where credentials were saved.
        """
        if isinstance(content, bytes):
            parsed = json.loads(content.decode("utf-8"))
        elif isinstance(content, str):
            parsed = json.loads(content)
        else:
            parsed = content

        if "installed" not in parsed and "web" not in parsed:
            raise ValueError(
                "Invalid Google OAuth Client Secrets JSON. Expected 'installed' or 'web' root key."
            )

        self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.credentials_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)

        return self.credentials_path

    def disconnect(self) -> bool:
        """Deletes the stored token.json from disk.

        Returns:
            True if the token was removed, False if it did not exist.
        """
        self._credentials = None
        if self.token_path.exists():
            self.token_path.unlink()
            return True
        return False

    @staticmethod
    def decode_mime_body(payload: dict[str, Any]) -> str:
        """Decodes plain-text body from a Gmail MIME payload dictionary."""
        if "parts" in payload:
            for part in payload["parts"]:
                if (
                    part.get("mimeType") == "text/plain"
                    and "data" in part.get("body", {})
                ):
                    raw_data = part["body"]["data"]
                    return base64.urlsafe_b64decode(raw_data).decode(
                        "utf-8", errors="ignore"
                    )

        if "body" in payload and "data" in payload["body"]:
            raw_data = payload["body"]["data"]
            return base64.urlsafe_b64decode(raw_data).decode(
                "utf-8", errors="ignore"
            )

        return ""
