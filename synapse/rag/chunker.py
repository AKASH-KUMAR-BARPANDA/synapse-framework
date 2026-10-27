"""Text chunking utilities for RAG ingestion in Synapse."""

from __future__ import annotations

import hashlib
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from synapse.config import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE


class DocumentChunker:
    """Splits arbitrary text and connector payloads into deterministic LangChain Document chunks."""

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        """Initializes the document chunker.

        Args:
            chunk_size: Maximum character length per chunk. Defaults to 280.
            chunk_overlap: Character overlap between consecutive chunks. Defaults to 30.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
            length_function=len,
        )

    @staticmethod
    def _generate_chunk_id(source: str, parent_id: str, index: int) -> str:
        seed = f"{source}:{parent_id}:{index}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

    def chunk_text(
        self,
        text: str,
        source: str = "text",
        metadata: dict[str, Any] | None = None,
        parent_id: str | None = None,
    ) -> list[Document]:
        """Splits raw text into indexed LangChain Document chunks."""
        clean_text = text.strip()
        if not clean_text:
            return []

        base_meta = metadata.copy() if metadata else {}
        base_meta["source"] = source
        doc_id = (
            parent_id
            or hashlib.sha256(clean_text[:128].encode("utf-8")).hexdigest()[:12]
        )

        raw_chunks = self.splitter.split_text(clean_text)
        documents: list[Document] = []
        for idx, chunk in enumerate(raw_chunks):
            chunk_meta = {
                **base_meta,
                "parent_id": doc_id,
                "chunk_index": idx,
                "chunk_id": self._generate_chunk_id(source, doc_id, idx),
            }
            documents.append(Document(page_content=chunk, metadata=chunk_meta))

        return documents

    def chunk_email(self, email_data: dict[str, Any]) -> list[Document]:
        """Formats and splits an email dictionary into Document chunks."""
        email_id = str(email_data.get("id", ""))
        subject = str(email_data.get("subject", "No Subject")).strip()
        sender = str(
            email_data.get("from") or email_data.get("sender") or "Unknown Sender"
        ).strip()
        recipients = str(email_data.get("to", "Me")).strip()
        date_str = str(email_data.get("date", "")).strip()
        body = str(email_data.get("body", "")).strip()
        is_unread = bool(email_data.get("is_unread", False))
        read_tag = "UNREAD" if is_unread else "READ"

        if not body and not subject:
            return []

        header_context = (
            f"[EMAIL | {read_tag}] Subject: {subject} | From: {sender} | To: {recipients}"
        )
        full_text = f"{header_context}\nDate: {date_str}\n\n{body}"

        base_meta: dict[str, Any] = {
            "source": "gmail",
            "email_id": email_id,
            "subject": subject,
            "sender": sender,
            "recipients": recipients,
            "date": date_str,
            "is_unread": is_unread,
            "type": "Email",
        }

        raw_chunks = self.splitter.split_text(full_text)
        documents: list[Document] = []
        for idx, chunk in enumerate(raw_chunks):
            chunk_meta = {
                **base_meta,
                "chunk_index": idx,
                "chunk_id": self._generate_chunk_id("gmail", email_id, idx),
            }
            documents.append(Document(page_content=chunk, metadata=chunk_meta))

        return documents

    def chunk_chat_turn(
        self,
        user_message: str,
        assistant_response: str,
        session_id: str,
        turn_index: int,
    ) -> list[Document]:
        """Splits a single conversation turn into Document chunks."""
        content = (
            f"User: {user_message.strip()}\nAssistant: {assistant_response.strip()}"
        )
        base_meta: dict[str, Any] = {
            "source": "chat_history",
            "session_id": session_id,
            "turn_index": turn_index,
            "type": "Conversation",
        }
        return self.chunk_text(
            text=content,
            source="chat_history",
            metadata=base_meta,
            parent_id=f"{session_id}_{turn_index}",
        )

    def chunk_mcp_record(
        self,
        server_name: str,
        tool_name: str,
        record: dict[str, Any],
    ) -> list[Document]:
        """Normalizes and splits a record from any connector/MCP tool."""
        if server_name == "gmail":
            return self.chunk_email(record)

        rec_id = str(
            record.get("id")
            or record.get("page_id")
            or record.get("url")
            or hashlib.sha256(str(record).encode("utf-8")).hexdigest()[:12]
        )
        title = str(
            record.get("title")
            or record.get("subject")
            or record.get("name")
            or record.get("summary")
            or f"{server_name.upper()} Record"
        ).strip()
        author = str(
            record.get("sender")
            or record.get("from")
            or record.get("author")
            or record.get("owner")
            or record.get("creator")
            or server_name
        ).strip()
        date_str = str(
            record.get("date")
            or record.get("last_edited_time")
            or record.get("created_at")
            or record.get("updated_at")
            or ""
        ).strip()
        body = str(
            record.get("body")
            or record.get("content")
            or record.get("text")
            or record.get("description")
            or record.get("snippet")
            or ""
        ).strip()
        url = str(record.get("url") or "").strip()

        if not body and not title:
            return []

        header = f"[{server_name.upper()} | {tool_name}] Title: {title} | Source: {author}"
        if url:
            header += f" | URL: {url}"
        full_text = f"{header}\nDate: {date_str}\n\n{body}".strip()

        base_meta: dict[str, Any] = {
            "source": server_name,
            "tool": tool_name,
            "record_id": rec_id,
            "subject": title,
            "sender": author,
            "date": date_str,
            "url": url,
            "type": str(record.get("type") or server_name.capitalize()),
        }

        raw_chunks = self.splitter.split_text(full_text)
        documents: list[Document] = []
        for idx, chunk in enumerate(raw_chunks):
            chunk_meta = {
                **base_meta,
                "chunk_index": idx,
                "chunk_id": self._generate_chunk_id(server_name, rec_id, idx),
            }
            documents.append(Document(page_content=chunk, metadata=chunk_meta))

        return documents

    def split_text(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        source: str | None = None,
    ) -> list[Document]:
        """Convenience method splitting text into Document chunks with metadata."""
        src = source or (metadata.get("source") if metadata else None) or "text"
        return self.chunk_text(text=text, source=src, metadata=metadata)
