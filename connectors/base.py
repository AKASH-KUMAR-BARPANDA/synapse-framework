
import os
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from app.config import (
    GMAIL_CREDENTIALS_FILE,
    GMAIL_TOKEN_FILE,
    NOTION_API_KEY,
)


class GoogleServiceManager:

    def __init__(
        self,
        creds_path: Optional[Path] = None,
        token_path: Optional[Path] = None
    ):
        self.creds_path = Path(creds_path) if creds_path else GMAIL_CREDENTIALS_FILE
        self.token_path = Path(token_path) if token_path else GMAIL_TOKEN_FILE
        self.credentials: Optional[Credentials] = None

    def authenticate(self, scopes: List[str]) -> Credentials:
        if self.token_path.exists():
            self.credentials = Credentials.from_authorized_user_file(str(self.token_path), scopes)

        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
            else:
                if not self.creds_path.exists():
                    raise FileNotFoundError(
                        f"Missing credentials file at: {self.creds_path}. "
                        "Please verify GMAIL_CREDENTIALS_FILE in app/config.py."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(self.creds_path), scopes)
                self.credentials = flow.run_local_server(port=0)

            with open(self.token_path, "w", encoding="utf-8") as token_file:
                token_file.write(self.credentials.to_json())

        return self.credentials

    def get_service(self, api_name: str, version: str, scopes: List[str]) -> Resource:
        creds = self.authenticate(scopes)
        return build(api_name, version, credentials=creds)

    @staticmethod
    def decode_mime_body(payload: Dict[str, Any]) -> str:
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                    raw_data = part["body"]["data"]
                    return base64.urlsafe_b64decode(raw_data).decode("utf-8", errors="ignore")

        if "body" in payload and "data" in payload["body"]:
            raw_data = payload["body"]["data"]
            return base64.urlsafe_b64decode(raw_data).decode("utf-8", errors="ignore")

        return ""


class NotionServiceManager:

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or NOTION_API_KEY
        self.base_url = "https://api.notion.com/v1"

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }