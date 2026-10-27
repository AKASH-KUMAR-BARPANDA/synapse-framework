"""Local Ollama model provider for Synapse."""

from __future__ import annotations

import json
import re
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from synapse.config import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_TEMPERATURE,
)
from synapse.models.base import BaseModelProvider


class OllamaModel(BaseModelProvider):
    """Local Ollama LLM provider (e.g. Qwen 2.5, Llama 3, Mistral).

    Attributes:
        base_url: Base HTTP address of the running Ollama daemon.
        model_name: Target model tag (default: 'qwen2.5:0.5b').
        temperature: Default sampling temperature.
        num_ctx: Context window size configured for Ollama requests.
    """

    def __init__(
        self,
        model: str = DEFAULT_OLLAMA_MODEL,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        temperature: float = DEFAULT_TEMPERATURE,
        num_ctx: int = 4096,
        timeout: float = 60.0,
        num_predict: int = 256,
    ) -> None:
        """Initializes the Ollama model provider.

        Args:
            model: Model tag registered in Ollama. Defaults to 'qwen2.5:0.5b'.
            base_url: Base URL of the Ollama server. Defaults to 'http://localhost:11434'.
            temperature: Sampling temperature. Defaults to 0.1.
            num_ctx: Context window size. Defaults to 4096.
            timeout: HTTP request timeout in seconds. Defaults to 60.0.
            num_predict: Maximum tokens to generate per response turn. Defaults to 256.
        """
        super().__init__(model_name=model, temperature=temperature)
        self.base_url = base_url.rstrip("/")
        self.num_ctx = num_ctx
        self.timeout = timeout
        self.num_predict = num_predict

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streams response tokens from the local Ollama instance.

        Args:
            messages: List of chat messages with 'role' and 'content'.
            temperature: Optional temperature override.

        Yields:
            Token strings as they are generated.
        """
        temp = self.temperature if temperature is None else temperature
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temp,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as stream:
                    if stream.status_code != 200:
                        yield (
                            f"Ollama returned HTTP {stream.status_code}. "
                            f"Please verify that model '{self.model_name}' is downloaded (`ollama pull {self.model_name}`)."
                        )
                        return

                    async for chunk in stream.aiter_lines():
                        if not chunk:
                            continue
                        try:
                            data = json.loads(chunk)
                            token = data.get("message", {}).get("content", "")
                            if token:
                                yield token
                        except (json.JSONDecodeError, KeyError):
                            continue
        except (httpx.ConnectError, httpx.ConnectTimeout):
            yield (
                f"Cannot reach Ollama at {self.base_url}. "
                f"Please ensure the Ollama daemon is running (`ollama serve`), "
                f"or switch to an alternative model provider in Settings."
            )
        except Exception as e:
            yield f"Ollama generation error: {e}"

    async def generate(
        self,
        prompt: str,
        temperature: float | None = None,
        format: str | None = None,
    ) -> str:
        """Generates a complete non-streaming response from Ollama.

        Args:
            prompt: Text prompt string.
            temperature: Optional temperature override.
            format: Optional output format (e.g. 'json').

        Returns:
            The complete response text string.
        """
        temp = self.temperature if temperature is None else temperature
        payload: dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temp,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
            },
        }
        if format:
            payload["format"] = format

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                res.raise_for_status()
                data = res.json()
                return str(data.get("response", "")).strip()
        except (httpx.ConnectError, httpx.ConnectTimeout):
            return f"[Error: Cannot reach Ollama at {self.base_url}. Ensure Ollama is running.]"
        except Exception as e:
            return f"[Error from Ollama: {e}]"

    async def extract_triples(self, text: str) -> list[dict[str, str]]:
        """Extracts typed knowledge graph triples from text using Ollama.

        Args:
            text: Unstructured text content.

        Returns:
            A list of dictionary triples.
        """
        clean_text = text.strip()
        if not clean_text:
            return []

        prompt = (
            "You are an information extraction system. Extract key relational triples from the text.\n"
            "Valid types: Person, Email, Project, Tool, Topic, Default.\n"
            "Return ONLY a valid JSON list of objects without explanations or markdown backticks.\n\n"
            "Example format:\n"
            '[{"source": "Sarah", "source_type": "Person", "relation": "DISCUSSES", "target": "Synapse", "target_type": "Project"}]\n\n'
            f"TEXT:\n{clean_text}\n\n"
            "JSON:"
        )

        try:
            raw_text = await self.generate(prompt, temperature=0.0, format="json")
            if not raw_text or raw_text.startswith("[Error:"):
                return []
            cleaned = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                raw_text,
                flags=re.MULTILINE,
            ).strip()
            match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(0)
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                parsed = parsed.get("triples") or parsed.get("data") or (list(parsed.values())[0] if parsed.values() and isinstance(list(parsed.values())[0], list) else [])

            if isinstance(parsed, list):
                valid_triples: list[dict[str, str]] = []
                for item in parsed:
                    if (
                        isinstance(item, dict)
                        and "source" in item
                        and "relation" in item
                        and "target" in item
                    ):
                        valid_triples.append({
                            "source": str(item["source"]).strip(),
                            "relation": (
                                str(item["relation"])
                                .strip()
                                .upper()
                                .replace(" ", "_")
                            ),
                            "target": str(item["target"]).strip(),
                            "source_type": (
                                str(item.get("source_type", "Default"))
                                .strip()
                                .title()
                            ),
                            "target_type": (
                                str(item.get("target_type", "Default"))
                                .strip()
                                .title()
                            ),
                        })
                return valid_triples
        except Exception:
            return []

        return []

    async def decide_tool_calls(
        self,
        user_message: str,
        candidate_tools: list[dict[str, Any]],
        fallback_calls: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Determines which candidate MCP tool(s) to execute using Ollama.

        Args:
            user_message: Natural-language message from the user.
            candidate_tools: List of tool schema descriptors across connectors.
            fallback_calls: Fallback calls used if model outputs invalid JSON.

        Returns:
            A list of validated tool call dictionaries.
        """
        text = (user_message or "").strip()
        if not text or not candidate_tools:
            return []

        catalog_lines: list[str] = []
        valid_keys: dict[tuple[str, str], dict[str, Any]] = {}
        for idx, t in enumerate(candidate_tools, start=1):
            srv = str(t.get("server", "")).strip()
            name = str(t.get("name", "")).strip()
            desc = str(t.get("description", "")).strip()
            schema = json.dumps(t.get("inputSchema", {}).get("properties", {}))
            catalog_lines.append(
                f'{idx}. server="{srv}", tool="{name}" — {desc}\n   arguments schema: {schema}'
            )
            valid_keys[(srv, name)] = t
            valid_keys[("", name)] = t
            valid_keys[(srv.lower(), name.lower())] = t
            valid_keys[("", name.lower())] = t
            valid_keys[(srv.lower(), f"{srv.lower()}_{name.lower()}")] = t

        catalog_text = "\n".join(catalog_lines)
        tool_prompt = (
            "You are a multi-tool router for a personal AI assistant.\n"
            "Available Tools:\n"
            f"{catalog_text}\n\n"
            "Decide which tool(s) must be called to answer the user's message.\n"
            "- Only call a tool if the user's message actually requires fetching data from that service.\n"
            "- For Gmail unread queries, include 'is:unread' in the Gmail query (e.g. 'label:INBOX is:unread').\n"
            "Return ONLY valid JSON without markdown backticks in this exact format:\n"
            '{"tool_calls": [{"server": "gmail", "tool": "search_emails", "arguments": {"query": "label:INBOX is:unread", "max_results": 5}}]}\n'
            "or if no tool is needed:\n"
            '{"tool_calls": []}\n\n'
            f"USER MESSAGE: {text}\n"
            "JSON:"
        )

        try:
            raw_text = await self.generate(tool_prompt, temperature=0.0, format="json")
            if not raw_text or raw_text.startswith("[Error:"):
                return []
            cleaned = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                raw_text,
                flags=re.MULTILINE,
            ).strip()
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(0)
            parsed = json.loads(cleaned)

            if isinstance(parsed, dict):
                if parsed.get("call_tool") is False:
                    return []
                raw_calls = parsed.get("tool_calls")
                if isinstance(raw_calls, list):
                    if len(raw_calls) == 0:
                        return []
                    validated: list[dict[str, Any]] = []
                    for item in raw_calls:
                        if not isinstance(item, dict):
                            continue
                        srv = str(item.get("server") or "").strip()
                        tl = str(item.get("tool") or item.get("name") or "").strip()
                        spec = (
                            valid_keys.get((srv, tl))
                            or valid_keys.get(("", tl))
                            or valid_keys.get((srv.lower(), tl.lower()))
                            or valid_keys.get(("", tl.lower()))
                        )
                        if not spec:
                            continue
                        resolved_srv = str(spec.get("server") or srv)
                        resolved_tl = str(spec.get("name") or tl)
                        args = item.get("arguments")
                        if not isinstance(args, dict):
                            args = {}
                        validated.append({
                            "server": resolved_srv,
                            "tool": resolved_tl,
                            "arguments": args,
                        })
                    return validated
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, httpx.HTTPError):
            pass

        return list(fallback_calls or [])
