"""OpenAI and OpenAI-compatible API model provider for Synapse."""

from __future__ import annotations

import json
import os
import re
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from synapse.config import DEFAULT_OPENAI_MODEL, DEFAULT_TEMPERATURE
from synapse.models.base import BaseModelProvider


class OpenAIModel(BaseModelProvider):
    """OpenAI API and compatible endpoints (Groq, OpenRouter, DeepSeek, vLLM).

    Attributes:
        api_key: OpenAI API key (reads from OPENAI_API_KEY if omitted).
        base_url: API endpoint URL (default: 'https://api.openai.com/v1').
        model_name: Model identifier (default: 'gpt-4o-mini').
        organization: Optional organization header.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_OPENAI_MODEL,
        base_url: str = "https://api.openai.com/v1",
        temperature: float = DEFAULT_TEMPERATURE,
        organization: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        """Initializes the OpenAI model provider.

        Args:
            api_key: Secret API key. If None, reads from OPENAI_API_KEY environment variable.
            model: Model name string. Defaults to 'gpt-4o-mini'.
            base_url: Base endpoint URL. Defaults to 'https://api.openai.com/v1'.
            temperature: Sampling temperature. Defaults to 0.1.
            organization: Optional OpenAI organization ID.
            timeout: HTTP request timeout in seconds. Defaults to 60.0.
        """
        super().__init__(model_name=model, temperature=temperature)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.organization = organization
        self.timeout = timeout

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.organization:
            headers["OpenAI-Organization"] = self.organization
        return headers

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streams response tokens from the OpenAI chat completions endpoint."""
        temp = self.temperature if temperature is None else temperature
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "temperature": temp,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                ) as stream:
                    if stream.status_code in (401, 403):
                        yield "OpenAI authentication failed: Please verify your OpenAI API key in Settings."
                        return
                    if stream.status_code != 200:
                        yield f"OpenAI API returned HTTP {stream.status_code}."
                        return

                    async for chunk in stream.aiter_lines():
                        if not chunk or not chunk.startswith("data: "):
                            continue
                        data_str = chunk[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                token = delta.get("content", "")
                                if token:
                                    yield token
                        except json.JSONDecodeError:
                            continue
        except (httpx.ConnectError, httpx.ConnectTimeout):
            yield f"Cannot reach OpenAI API at {self.base_url}. Please check your network connection."
        except Exception as e:
            yield f"OpenAI error: {e}"

    async def generate(
        self,
        prompt: str,
        temperature: float | None = None,
    ) -> str:
        """Generates a non-streaming response for a prompt string."""
        temp = self.temperature if temperature is None else temperature
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": temp,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload,
                )
                res.raise_for_status()
                data = res.json()
                choices = data.get("choices", [])
                if choices:
                    return str(
                        choices[0].get("message", {}).get("content", "")
                    ).strip()
                return ""
        except (httpx.ConnectError, httpx.ConnectTimeout):
            return f"[Error: Cannot connect to OpenAI API at {self.base_url}. Check your internet connection.]"
        except Exception as e:
            return f"[Error from OpenAI: {e}]"

    async def extract_triples(self, text: str) -> list[dict[str, str]]:
        """Extracts relational triples using OpenAI structured prompt."""
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
            raw_text = await self.generate(prompt, temperature=0.0)
            cleaned = re.sub(
                r"^```(?:json)?\s*|\s*```$",
                "",
                raw_text,
                flags=re.MULTILINE,
            ).strip()
            match = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(0)
            parsed = json.loads(cleaned)

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
        """Decides tool calls using OpenAI JSON reasoning."""
        text = (user_message or "").strip()
        if not text or not candidate_tools:
            return []

        catalog_lines = []
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
            raw_text = await self.generate(tool_prompt, temperature=0.0)
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
                raw_calls = parsed.get("tool_calls")
                if isinstance(raw_calls, list):
                    validated: list[dict[str, Any]] = []
                    for item in raw_calls:
                        if not isinstance(item, dict):
                            continue
                        srv = str(item.get("server") or "").strip()
                        tl = str(item.get("tool") or item.get("name") or "").strip()
                        spec = valid_keys.get((srv, tl)) or valid_keys.get(("", tl))
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
                    if validated:
                        return validated
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, httpx.HTTPError):
            pass  # nosec B110

        return list(fallback_calls or [])
