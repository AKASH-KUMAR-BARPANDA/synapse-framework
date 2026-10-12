"""Language model providers and factory functions for Synapse."""

from __future__ import annotations

from typing import Any

from synapse.models.base import BaseModelProvider
from synapse.models.gemini import GeminiModel
from synapse.models.ollama import OllamaModel
from synapse.models.openai import OpenAIModel

# Developer-friendly aliases matching different casing conventions
ollama = OllamaModel
Ollama = OllamaModel
openAI = OpenAIModel
openai = OpenAIModel
OpenAI = OpenAIModel
Gemini = GeminiModel
gemini = GeminiModel
Gemimi = GeminiModel
gemimi = GeminiModel


def get_model(
    provider_or_name: str | BaseModelProvider = "ollama",
    **kwargs: Any,
) -> BaseModelProvider:
    """Factory function returning a configured `BaseModelProvider`.

    Args:
        provider_or_name: Either a provider string ('ollama', 'openai', 'gemini')
            or an existing `BaseModelProvider` instance.
        **kwargs: Provider-specific configuration arguments (model, api_key, base_url, etc.).

    Returns:
        A concrete `BaseModelProvider` instance.

    Example:
        ```python
        model = get_model("openai", api_key="sk-...", model="gpt-4o")
        ```
    """
    if isinstance(provider_or_name, BaseModelProvider):
        return provider_or_name

    name = str(provider_or_name).lower().strip()
    if name in {"ollama", "local", "qwen"}:
        return OllamaModel(**kwargs)
    elif name in {"openai", "chatgpt", "gpt"}:
        return OpenAIModel(**kwargs)
    elif name in {"gemini", "google"}:
        return GeminiModel(**kwargs)
    else:
        raise ValueError(
            f"Unknown model provider: '{provider_or_name}'. "
            "Supported providers: 'ollama', 'openai', 'gemini'."
        )


__all__ = [
    "BaseModelProvider",
    "Gemini",
    "GeminiModel",
    "Ollama",
    "OllamaModel",
    "OpenAI",
    "OpenAIModel",
    "gemini",
    "get_model",
    "ollama",
    "openAI",
    "openai",
]
