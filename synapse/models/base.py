"""Abstract base class for Synapse language model providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any


class BaseModelProvider(ABC):
    """Abstract interface for LLM providers supported by the Synapse framework.

    Subclasses must implement streaming chat, single prompt completion,
    knowledge graph triple extraction, and multi-MCP tool routing.
    """

    def __init__(self, model_name: str, temperature: float = 0.1) -> None:
        """Initializes the base model provider.

        Args:
            model_name: Identifier of the target model (e.g. 'qwen2.5:0.5b', 'gpt-4o').
            temperature: Sampling temperature in the range [0.0, 1.0].
        """
        self.model_name = model_name
        self.temperature = temperature

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streams response tokens for a multi-turn chat sequence.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
            temperature: Optional per-request temperature override.

        Yields:
            Incremental string tokens as they are produced by the model.
        """
        ...

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float | None = None,
    ) -> str:
        """Generates a complete non-streaming response for a single prompt.

        Args:
            prompt: Text prompt string.
            temperature: Optional per-request temperature override.

        Returns:
            The complete response text string.
        """
        ...

    @abstractmethod
    async def extract_triples(self, text: str) -> list[dict[str, str]]:
        """Extracts relational entity triples from unstructured text.

        Args:
            text: Unstructured text content.

        Returns:
            A list of dictionary triples containing 'source', 'relation', 'target',
            'source_type', and 'target_type'.
        """
        ...

    @abstractmethod
    async def decide_tool_calls(
        self,
        user_message: str,
        candidate_tools: list[dict[str, Any]],
        fallback_calls: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Selects which candidate tool(s) to execute for a user message.

        Args:
            user_message: Natural language prompt submitted by the user.
            candidate_tools: List of tool schemas across registered connectors.
            fallback_calls: Optional fallback tool calls if the model fails or times out.

        Returns:
            A list of validated tool calls: [{'server': '...', 'tool': '...', 'arguments': {...}}].
        """
        ...

    async def close(self) -> None:
        """Releases any client connections or background resources."""
        return
