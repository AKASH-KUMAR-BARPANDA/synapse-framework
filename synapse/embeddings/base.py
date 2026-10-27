"""Pluggable embedding providers and model resolution engine for Synapse."""

from __future__ import annotations

import os
import warnings
from typing import Any

from langchain_core.embeddings import Embeddings

from synapse.config import DEFAULT_EMBEDDING_MODEL


class LazyFastEmbedEmbeddings(Embeddings):
    """Zero-overhead lazy wrapper for FastEmbed ONNX local embeddings.

    Defers model download and ONNX runtime initialization until the first
    `embed_documents` or `embed_query` call. This prevents app startup freezes
    and keeps stdout completely clean for MCP stdio protocol communication.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        max_length: int | None = None,
        **kwargs: Any,
    ) -> None:
        self.model_name = model_name
        self.max_length = max_length
        self.kwargs = kwargs
        self._inner: Embeddings | None = None

    def _get_inner(self) -> Embeddings:
        if self._inner is None:
            # Set environment variable to suppress progress bars that corrupt MCP stdio
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
            os.environ["TOKENIZERS_PARALLELISM"] = "false"
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=DeprecationWarning)
                    from langchain_community.embeddings.fastembed import FastEmbedEmbeddings

                extra_args: dict[str, Any] = dict(self.kwargs)
                if self.max_length is not None:
                    extra_args["max_length"] = self.max_length
                self._inner = FastEmbedEmbeddings(model_name=self.model_name, **extra_args)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load FastEmbed model '{self.model_name}': {e}. "
                    "Ensure 'fastembed' is installed."
                ) from e
        return self._inner

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embeds a list of documents."""
        return self._get_inner().embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        """Embeds a query string."""
        return self._get_inner().embed_query(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Asynchronously embeds documents."""
        return await self._get_inner().aembed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        """Asynchronously embeds a query."""
        return await self._get_inner().aembed_query(text)


class EmbeddingModelRegistry:
    """Friendly shorthand aliases for popular embedding models."""

    ALIASES: dict[str, str] = {
        # MiniLM variants
        "minilm": "sentence-transformers/all-MiniLM-L6-v2",
        "all-minilm": "sentence-transformers/all-MiniLM-L6-v2",
        "all-minilm-l6-v2": "sentence-transformers/all-MiniLM-L6-v2",
        "minilm-l6": "sentence-transformers/all-MiniLM-L6-v2",
        "paraphrase-minilm": "sentence-transformers/paraphrase-MiniLM-L6-v2",
        # BGE variants (Default FastEmbed models)
        "fastembed": DEFAULT_EMBEDDING_MODEL,
        "bge": DEFAULT_EMBEDDING_MODEL,
        "bge-small": "BAAI/bge-small-en-v1.5",
        "bge-base": "BAAI/bge-base-en-v1.5",
        "bge-large": "BAAI/bge-large-en-v1.5",
        # Nomic
        "nomic": "nomic-ai/nomic-embed-text-v1.5",
        "nomic-embed": "nomic-ai/nomic-embed-text-v1.5",
        # Multilingual E5
        "e5": "intfloat/multilingual-e5-large",
        "multilingual-e5": "intfloat/multilingual-e5-large",
        # OpenAI models
        "openai": "text-embedding-3-small",
        "text-embedding-3-small": "text-embedding-3-small",
        "text-embedding-3-large": "text-embedding-3-large",
        "ada": "text-embedding-ada-002",
        "text-embedding-ada-002": "text-embedding-ada-002",
    }


def fastembed(
    model_name: str = "BAAI/bge-small-en-v1.5",
    max_length: int | None = None,
    **kwargs: Any,
) -> Any:
    """Initializes FastEmbed ONNX local embeddings (ultra-fast, zero-PyTorch, lazy-loaded).

    Args:
        model_name: Model name or HuggingFace ID (e.g. 'BAAI/bge-small-en-v1.5',
            'sentence-transformers/all-MiniLM-L6-v2', 'nomic-ai/nomic-embed-text-v1.5').
        max_length: Optional maximum sequence length.
        **kwargs: Extra arguments forwarded to FastEmbedEmbeddings.

    Returns:
        LazyFastEmbedEmbeddings instance (defers loading until first embedding call).
    """
    resolved_model = EmbeddingModelRegistry.ALIASES.get(model_name.lower(), model_name)
    return LazyFastEmbedEmbeddings(
        model_name=resolved_model,
        max_length=max_length,
        **kwargs,
    )


def minilm(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    **kwargs: Any,
) -> Any:
    """Convenience factory for MiniLM embeddings via FastEmbed ONNX runtime.

    Args:
        model_name: MiniLM model variant. Defaults to 'sentence-transformers/all-MiniLM-L6-v2'.
        **kwargs: Extra parameters passed to FastEmbed.

    Returns:
        FastEmbedEmbeddings configured with all-MiniLM-L6-v2.
    """
    return fastembed(model_name=model_name, **kwargs)


def openai_embeddings(
    model: str = "text-embedding-3-small",
    api_key: str | None = None,
    **kwargs: Any,
) -> Any:
    """Initializes OpenAI cloud vector embeddings.

    Args:
        model: OpenAI embedding model name. Defaults to 'text-embedding-3-small'.
        api_key: Optional OpenAI API key (reads OPENAI_API_KEY env if omitted).
        **kwargs: Extra parameters passed to OpenAIEmbeddings.

    Returns:
        OpenAIEmbeddings instance.
    """
    try:
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(model=model, api_key=api_key, **kwargs)
    except ImportError:
        try:
            from langchain_community.embeddings import OpenAIEmbeddings

            return OpenAIEmbeddings(model=model, openai_api_key=api_key, **kwargs)
        except Exception as e:
            raise ImportError(
                "OpenAI embeddings require 'langchain-openai'. "
                "Install it via 'pip install langchain-openai'."
            ) from e


def ollama_embeddings(
    model: str = "nomic-embed-text",
    base_url: str = "http://localhost:11434",
    **kwargs: Any,
) -> Any:
    """Initializes Ollama local embeddings.

    Args:
        model: Model tag installed in Ollama (e.g. 'nomic-embed-text', 'all-minilm').
        base_url: Ollama daemon URL. Defaults to 'http://localhost:11434'.
        **kwargs: Extra parameters.

    Returns:
        OllamaEmbeddings instance.
    """
    try:
        from langchain_community.embeddings import OllamaEmbeddings

        return OllamaEmbeddings(model=model, base_url=base_url, **kwargs)
    except Exception as e:
        raise ImportError(
            f"Failed to load Ollama embeddings: {e}. "
            "Ensure 'langchain-community' and Ollama are available."
        ) from e


def huggingface_embeddings(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    **kwargs: Any,
) -> Any:
    """Initializes PyTorch HuggingFace sentence-transformers embeddings.

    Args:
        model_name: HuggingFace model repo name.
        **kwargs: Extra parameters.

    Returns:
        HuggingFaceEmbeddings instance.
    """
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name=model_name, **kwargs)
    except Exception:
        # Fall back to FastEmbed for identical weights with 0 PyTorch
        return fastembed(model_name=model_name, **kwargs)


def resolve_embedding(
    embedding: str | Any | None = None,
    embedding_model: str | None = None,
    embedding_function: Any | None = None,
    **kwargs: Any,
) -> Any:
    """Flexible resolver converting strings, aliases, or objects into an embedding instance.

    Supported patterns:
        - None: Defaults to 'BAAI/bge-small-en-v1.5' via FastEmbed
        - 'minilm' or 'all-minilm-l6-v2': MiniLM ONNX embedding
        - 'fastembed' or 'bge-small': BGE Small ONNX embedding
        - 'openai' or 'text-embedding-3-small': OpenAI cloud embedding
        - 'ollama' or 'nomic-embed-text': Local Ollama embedding
        - Custom Embeddings object: Returned as-is

    Args:
        embedding: Model alias string, HuggingFace ID, or Embeddings instance.
        embedding_model: Backward-compatible alias for embedding string.
        embedding_function: Backward-compatible alias for custom object.
        **kwargs: Extra keyword arguments forwarded to the provider.

    Returns:
        An initialized embedding function satisfying the LangChain Embeddings protocol.
    """
    # 1. Custom pre-instantiated object passed
    target = embedding if embedding is not None else (embedding_function or embedding_model)

    if target is None:
        return fastembed(DEFAULT_EMBEDDING_MODEL, **kwargs)

    # Check if target is already an embedding instance (has embed_documents / embed_query)
    if hasattr(target, "embed_documents") and hasattr(target, "embed_query"):
        return target

    # Callable function wrapper
    if callable(target) and not isinstance(target, str):
        return target

    # 2. String alias resolution
    if isinstance(target, str):
        clean_str = target.strip()
        lower_str = clean_str.lower()

        # MiniLM shorthand
        if lower_str in ("minilm", "all-minilm", "all-minilm-l6-v2", "minilm-l6", "sentence-transformers/all-minilm-l6-v2"):
            return minilm(**kwargs)

        # FastEmbed / BGE shorthands
        if lower_str in ("fastembed", "bge", "bge-small", "baai/bge-small-en-v1.5"):
            return fastembed("BAAI/bge-small-en-v1.5", **kwargs)

        if lower_str in ("bge-base", "baai/bge-base-en-v1.5"):
            return fastembed("BAAI/bge-base-en-v1.5", **kwargs)

        if lower_str in ("bge-large", "baai/bge-large-en-v1.5"):
            return fastembed("BAAI/bge-large-en-v1.5", **kwargs)

        if lower_str in ("nomic", "nomic-embed", "nomic-ai/nomic-embed-text-v1.5"):
            return fastembed("nomic-ai/nomic-embed-text-v1.5", **kwargs)

        if lower_str in ("e5", "multilingual-e5", "intfloat/multilingual-e5-large"):
            return fastembed("intfloat/multilingual-e5-large", **kwargs)

        # OpenAI shorthands
        if lower_str in ("openai", "text-embedding-3-small", "text-embedding-3-large", "ada", "text-embedding-ada-002"):
            model_name = "text-embedding-3-small" if lower_str == "openai" else clean_str
            return openai_embeddings(model=model_name, **kwargs)

        # Ollama shorthands
        if lower_str.startswith("ollama:"):
            ollama_m = clean_str.split(":", 1)[1]
            return ollama_embeddings(model=ollama_m, **kwargs)

        if lower_str == "ollama":
            return ollama_embeddings(**kwargs)

        # Try FastEmbed with the arbitrary model name (supports HuggingFace repo names)
        try:
            return fastembed(clean_str, **kwargs)
        except Exception:
            # Fall back to HuggingFace Embeddings
            return huggingface_embeddings(clean_str, **kwargs)

    raise ValueError(f"Unsupported embedding specification: {target!r}")


__all__ = [
    "EmbeddingModelRegistry",
    "fastembed",
    "huggingface_embeddings",
    "minilm",
    "ollama_embeddings",
    "openai_embeddings",
    "resolve_embedding",
]
