"""Gmail connector for the Synapse framework."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from synapse.connectors.base import BaseConnector
from synapse.oauth.google import GoogleOAuthService

GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GmailConnector(BaseConnector):
    """Google Gmail connector for fetching, searching, and indexing emails.

    Attributes:
        oauth: Reusable GoogleOAuthService managing OAuth tokens and Discovery client.
    """

    def __init__(
        self,
        credentials_path: str | Path = "credentials.json",
        token_path: str | Path = "token.json",  # nosec B107
        oauth_service: GoogleOAuthService | None = None,
        scopes: list[str] | None = None,
    ) -> None:
        """Initializes the GmailConnector.

        Args:
            credentials_path: Path to OAuth client secrets JSON.
            token_path: Path to cached token JSON.
            oauth_service: Optional pre-configured GoogleOAuthService instance.
            scopes: Optional list of OAuth scopes.
        """
        super().__init__(
            name="gmail",
            description="Gmail inbox, unread/read emails, senders, and message threads",
            intent_regex=(
                r"\b(email|emails|e-mail|inbox|unread|mail|mails|message|messages|"
                r"gmail|sender|sent\s+me|from\s+[a-z0-9_.-]+|check\s+my\s+mail|"
                r"check\s+my\s+inbox|recent\s+threads)\b"
            ),
            default_tool="search_emails",
        )

        active_scopes = list(scopes or [GMAIL_READONLY_SCOPE])
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
        """Returns True if a valid Gmail OAuth token exists."""
        return self.oauth.is_authenticated()

    async def list_tools(self) -> list[dict[str, Any]]:
        """Returns the Gmail tool schemas."""
        return [
            {
                "server": self.name,
                "name": "search_emails",
                "description": (
                    "Search Gmail messages using Gmail query syntax "
                    "(e.g. 'label:INBOX', 'label:INBOX is:unread', 'from:Sender')."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "default": "label:INBOX",
                            "description": "Gmail search query string.",
                        },
                        "max_results": {
                            "type": "integer",
                            "default": 5,
                            "description": "Maximum number of messages to return.",
                        },
                    },
                },
            }
        ]

    def default_args_builder(self, user_message: str) -> dict[str, Any]:
        """Constructs smart Gmail query arguments from user natural language prompt."""
        text = (user_message or "").strip()
        q_lower = text.lower()
        wants_unread = bool(
            re.search(
                r"\b(unread|unseen|not\s+read|new\s+email|new\s+emails|new\s+message|new\s+messages)\b",
                q_lower,
            )
        )
        query = "label:INBOX is:unread" if wants_unread else "label:INBOX"

        from_match = re.search(
            r"\bfrom\s+([a-zA-Z0-9_.@-]+)", text, re.IGNORECASE
        )
        if from_match:
            sender_term = from_match.group(1).strip("?.!,")
            if sender_term.lower() not in {
                "my",
                "the",
                "recent",
                "inbox",
                "gmail",
                "email",
                "emails",
            }:
                query = (
                    f"from:{sender_term} is:unread"
                    if wants_unread
                    else f"from:{sender_term}"
                )

        return {"query": query, "max_results": 5}

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """Executes a Gmail tool via Google API."""
        args = arguments or {}
        if tool_name == "search_emails":
            query = str(args.get("query", "label:INBOX"))
            max_results = int(args.get("max_results", 5))
            return self.search_emails(query=query, max_results=max_results)
        raise ValueError(
            f"Unknown tool '{tool_name}' for connector '{self.name}'"
        )

    def search_emails(
        self,
        query: str = "label:INBOX",
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Searches Gmail using Google API Discovery client."""
        if not self.is_authenticated():
            return []

        service = self.oauth.get_service(
            api_name="gmail", version="v1", scopes=[GMAIL_READONLY_SCOPE]
        )
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages_meta = response.get("messages", [])
        if not messages_meta:
            return []

        results: list[dict[str, Any]] = []
        for meta in messages_meta:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=meta["id"], format="full")
                .execute()
            )

            payload = msg.get("payload", {})
            headers = payload.get("headers", [])
            label_ids = msg.get("labelIds", []) or []
            is_unread = "UNREAD" in label_ids

            subject = next(
                (h["value"] for h in headers if h["name"].lower() == "subject"),
                "No Subject",
            )
            sender = next(
                (h["value"] for h in headers if h["name"].lower() == "from"),
                "Unknown Sender",
            )
            recipient = next(
                (h["value"] for h in headers if h["name"].lower() == "to"), "Me"
            )
            date_str = next(
                (h["value"] for h in headers if h["name"].lower() == "date"), ""
            )

            body_text = GoogleOAuthService.decode_mime_body(payload)
            snippet = msg.get("snippet", "")

            results.append({
                "id": msg["id"],
                "subject": subject,
                "sender": sender,
                "to": recipient,
                "date": date_str,
                "is_unread": is_unread,
                "labels": label_ids,
                "snippet": snippet,
                "body": (body_text.strip() or snippet.strip()),
            })

        return results

    def chunk_record(
        self,
        tool_name: str,
        record: dict[str, Any],
    ) -> list[Document]:
        """Chunks an email record with rich unread metadata."""
        email_id = str(record.get("id", ""))
        subject = str(record.get("subject", "No Subject")).strip()
        sender = str(
            record.get("from") or record.get("sender") or "Unknown Sender"
        ).strip()
        recipients = str(record.get("to", "Me")).strip()
        date_str = str(record.get("date", "")).strip()
        body = str(record.get("body", "")).strip()
        is_unread = bool(record.get("is_unread", False))
        read_tag = "UNREAD" if is_unread else "READ"

        if not body and not subject:
            return []

        header = f"[EMAIL | {read_tag}] Subject: {subject} | From: {sender} | To: {recipients}"
        full_text = f"{header}\nDate: {date_str}\n\n{body}"

        base_meta = {
            "source": "gmail",
            "email_id": email_id,
            "subject": subject,
            "sender": sender,
            "recipients": recipients,
            "date": date_str,
            "is_unread": is_unread,
            "type": "Email",
            "chunk_id": f"gmail:{email_id}:0",
        }

        return [Document(page_content=full_text, metadata=base_meta)]

    def format_record(
        self,
        tool_name: str,
        record: dict[str, Any],
        index: int = 1,
    ) -> tuple[str, dict[str, Any], str]:
        """Formats email into context string, UI chunk, and knowledge graph triple."""
        is_unread = bool(record.get("is_unread", False))
        unread_badge = "UNREAD" if is_unread else "READ"
        subject = record.get("subject", "No Subject")
        sender = record.get("sender", "Unknown Sender")
        date_str = record.get("date", "")
        body_excerpt = (
            record.get("body") or record.get("snippet") or ""
        )[:600].strip()

        summary_line = (
            f"{index}. [{unread_badge}] Subject: {subject}\n"
            f"   From: {sender} | Date: {date_str}\n"
            f"   Content: {body_excerpt}"
        )

        live_chunk = {
            "page_content": (
                f"[EMAIL | {unread_badge}] Subject: {subject} | From: {sender}\n"
                f"Date: {date_str}\n\n{body_excerpt}"
            ),
            "metadata": {
                "source": "gmail_live",
                "subject": f"[{unread_badge}] {subject}",
                "sender": sender,
                "date": date_str,
                "is_unread": is_unread,
            },
            "source": "gmail_live",
            "subject": f"[{unread_badge}] {subject}",
            "chunk_id": f"live_gmail_{record.get('id', index)}",
        }

        triple = f"{sender} -> SENT -> {subject}"
        return summary_line, live_chunk, triple


# Developer-friendly alias matching user request
GmailConnectors = GmailConnector
