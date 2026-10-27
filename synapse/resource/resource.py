"""Resource management and document collection ingestion for Synapse."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from synapse.rag.chunker import DocumentChunker


class Resource:
    """Manages collections of static or dynamic documents for Synapse RAG retrieval.

    Supports ingesting raw strings, local files (.txt, .md, .pdf, .json, .csv),
    directories, and LangChain Document instances. Automatically chunks and embeds
    content for instant vector search and knowledge graph indexing.

    Example:
        ```python
        from synapse.resource import Resource

        # Ingest files or text
        res = Resource("knowledge_base")
        res.add("README.md")
        res.add("Quick note about architecture", title="Architecture")
        res.add(["docs/guide.md", "data/faq.txt"])

        # Pass to BaseApp:
        app = BaseApp(resource=res)
        ```
    """

    def __init__(
        self,
        name: str = "resource",
        documents: Document | str | Path | Sequence[Any] | None = None,
        chunker: DocumentChunker | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Initializes a Resource container.

        Args:
            name: Logical identifier for this resource collection.
            documents: Optional initial document, file path, or sequence of documents.
            chunker: Optional custom DocumentChunker instance.
            metadata: Arbitrary metadata associated with this resource.
        """
        self.name = name
        self.chunker = chunker or DocumentChunker()
        self.metadata = dict(metadata or {})
        self._raw_documents: list[Document] = []
        self._is_indexed: bool = False
        self._cached_chunks: list[Document] | None = None

        if documents is not None:
            self.add(documents)

    @property
    def documents(self) -> list[Document]:
        """Returns the list of raw Document objects in this resource."""
        return list(self._raw_documents)

    def load_documents(self) -> list[Document]:
        """Returns the list of loaded documents (alias for .documents)."""
        return self.documents

    @property
    def files(self) -> list[str]:
        """Returns the list of unique file source paths ingested."""
        seen = set()
        out = []
        for d in self._raw_documents:
            src = d.metadata.get("source") or d.metadata.get("path")
            if src and src not in seen:
                seen.add(src)
                out.append(src)
        return out

    def __len__(self) -> int:
        return len(self._raw_documents)

    def __repr__(self) -> str:
        return f"<Resource name='{self.name}' documents={len(self._raw_documents)}>"

    def add(
        self,
        *items: Any,
        **extra_metadata: Any,
    ) -> Resource:
        """Adds one or more documents, text strings, files, or directories to this resource.

        Args:
            *items: Variadic items to add. Each item can be a LangChain Document,
                raw text string, file Path, directory Path, or a list/tuple of them.
            **extra_metadata: Metadata merged into all items added during this call.

        Returns:
            The current Resource instance for fluent method chaining.
        """
        for item in items:
            self._ingest_item(item, extra_metadata)
        self._is_indexed = False
        self._cached_chunks = None
        return self

    def _ingest_item(self, item: Any, extra_metadata: dict[str, Any]) -> None:
        """Internal dispatcher for handling diverse input types."""
        if item is None:
            return

        if isinstance(item, (list, tuple, set)):
            for sub_item in item:
                self._ingest_item(sub_item, extra_metadata)
            return

        if isinstance(item, Document):
            merged_meta = {**item.metadata, **extra_metadata, "resource": self.name}
            self._raw_documents.append(
                Document(page_content=item.page_content, metadata=merged_meta)
            )
            return

        if isinstance(item, Path):
            self._ingest_path(item, extra_metadata)
            return

        if isinstance(item, str):
            clean_str = item.strip()
            # Check if this string points to an existing file or directory
            candidate = Path(clean_str)
            if candidate.exists():
                self._ingest_path(candidate, extra_metadata)
                return

            # Treat as raw text
            doc_id = hashlib.sha256(clean_str[:256].encode("utf-8")).hexdigest()[:12]
            meta = {
                "source": "resource_text",
                "resource": self.name,
                "record_id": doc_id,
                **extra_metadata,
            }
            self._raw_documents.append(
                Document(page_content=clean_str, metadata=meta)
            )
            return

        if isinstance(item, dict):
            content = str(
                item.get("content")
                or item.get("text")
                or item.get("body")
                or item.get("page_content")
                or json.dumps(item)
            )
            meta = {
                "source": "resource_dict",
                "resource": self.name,
                **item.get("metadata", {}),
                **extra_metadata,
            }
            self._raw_documents.append(Document(page_content=content, metadata=meta))
            return

        # Fallback for any other object: convert to string
        self._raw_documents.append(
            Document(
                page_content=str(item),
                metadata={"source": "resource_object", "resource": self.name, **extra_metadata},
            )
        )

    def _ingest_path(self, path: Path, extra_metadata: dict[str, Any]) -> None:
        """Reads a file or directory from disk."""
        resolved = path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Resource path does not exist: {resolved}")

        if resolved.is_dir():
            # Ingest all supported files in directory
            extensions = {".md", ".txt", ".json", ".csv", ".py", ".html", ".log", ".yaml", ".yml"}
            for child in sorted(resolved.rglob("*")):
                if child.is_file() and child.suffix.lower() in extensions:
                    self._ingest_file(child, extra_metadata)
            return

        if resolved.is_file():
            self._ingest_file(resolved, extra_metadata)

    def _ingest_file(self, file_path: Path, extra_metadata: dict[str, Any]) -> None:
        """Reads a single file into a Document."""
        suffix = file_path.suffix.lower()
        title = file_path.stem.replace("_", " ").replace("-", " ").title()

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            content = f"Error reading file {file_path.name}: {e}"

        meta = {
            "source": str(file_path),
            "filename": file_path.name,
            "title": title,
            "subject": title,
            "resource": self.name,
            "file_type": suffix.lstrip("."),
            **extra_metadata,
        }

        self._raw_documents.append(Document(page_content=content, metadata=meta))

    def add_text(
        self,
        text: str,
        title: str | None = None,
        source: str = "text",
        **metadata: Any,
    ) -> Resource:
        """Convenience helper to add raw text with a title."""
        meta = {"source": source, **metadata}
        if title:
            meta["title"] = title
            meta["subject"] = title
        return self.add(text, **meta)

    def add_file(
        self,
        file_path: str | Path,
        **metadata: Any,
    ) -> Resource:
        """Convenience helper to add a single file."""
        return self.add(Path(file_path), **metadata)

    def add_directory(
        self,
        dir_path: str | Path,
        **metadata: Any,
    ) -> Resource:
        """Convenience helper to ingest an entire directory."""
        return self.add(Path(dir_path), **metadata)

    def get_chunks(self) -> list[Document]:
        """Splits all ingested raw documents into indexable chunks using DocumentChunker."""
        if self._cached_chunks is not None:
            return self._cached_chunks

        all_chunks: list[Document] = []
        for doc in self._raw_documents:
            src = doc.metadata.get("source", self.name)
            rec_id = doc.metadata.get("record_id") or hashlib.sha256(
                doc.page_content[:128].encode("utf-8")
            ).hexdigest()[:12]
            chunks = self.chunker.chunk_text(
                text=doc.page_content,
                source=src,
                metadata=doc.metadata,
                parent_id=rec_id,
            )
            all_chunks.extend(chunks)
        self._cached_chunks = all_chunks
        return all_chunks

    def index_into(
        self,
        vector_store: Any | None = None,
        graph_store: Any | None = None,
    ) -> int:
        """Chunks and indexes this resource into vector store and knowledge graph.

        Args:
            vector_store: Optional vector store instance (LocalVectorStore, VectorStorage, BaseVectorDB).
            graph_store: Optional graph store instance (PersistentGraphStore, BaseGraphStore).

        Returns:
            The total number of chunks successfully processed.
        """
        chunks = self.get_chunks()
        if not chunks:
            return 0

        if vector_store is not None:
            vector_store.add_documents(chunks)

        if graph_store is not None:
            # Register resource node and links in knowledge graph with single atomic save
            if hasattr(graph_store, "add_node_entity"):
                graph_store.add_node_entity(
                    name=self.name,
                    entity_type="Resource",
                    attributes={"total_docs": len(self._raw_documents), "chunks": len(chunks)},
                    auto_save=False,
                )
            for doc in self._raw_documents:
                title = (
                    doc.metadata.get("title")
                    or doc.metadata.get("filename")
                    or doc.metadata.get("subject")
                    or (doc.page_content[:35].strip() + "...")
                )
                if title:
                    graph_store.add_relation(
                        source=self.name,
                        relation="CONTAINS",
                        target=str(title),
                        source_type="Resource",
                        target_type="Document",
                        auto_save=False,
                    )
            if hasattr(graph_store, "save"):
                try:
                    graph_store.save()
                except Exception:
                    pass  # nosec B110

        self._is_indexed = True
        return len(chunks)

    def to_dict(self) -> dict[str, Any]:
        """Serializes resource statistics into a dictionary."""
        return {
            "name": self.name,
            "document_count": len(self._raw_documents),
            "chunk_count": len(self.get_chunks()),
            "is_indexed": self._is_indexed,
            "metadata": self.metadata,
        }


__all__ = ["Resource"]
