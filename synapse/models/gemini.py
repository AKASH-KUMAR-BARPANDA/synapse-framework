"""Google Gemini API model provider for Synapse."""

from __future__ import annotations

import asyncio
import json
import os
import re
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from synapse.config import DEFAULT_GEMINI_MODEL, DEFAULT_TEMPERATURE
from synapse.models.base import BaseModelProvider


class GeminiModel(BaseModelProvider):
    """Google Gemini language model provider (e.g. gemini-3.5-flash, gemini-flash-latest).

    Attributes:
        api_key: Google AI Studio API key (reads from GEMINI_API_KEY if omitted).
        model_name: Model identifier (default: 'gemini-3.5-flash').
        temperature: Default sampling temperature.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_GEMINI_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        timeout: float = 60.0,
    ) -> None:
        """Initializes the Gemini model provider.

        Args:
            api_key: Google Gemini API key. If None, reads from GEMINI_API_KEY.
            model: Gemini model identifier. Defaults to DEFAULT_GEMINI_MODEL ('gemini-3.5-flash').
            temperature: Sampling temperature. Defaults to 0.1.
            timeout: HTTP request timeout in seconds. Defaults to 60.0.
        """
        super().__init__(model_name=model, temperature=temperature)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.timeout = timeout

    def _convert_messages(
        self, messages: list[dict[str, str]]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        system_instruction: str | None = None
        contents: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                system_instruction = content
            else:
                gemini_role = "model" if role == "assistant" else "user"
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": content}],
                })

        return system_instruction, contents

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streams response tokens from Google Gemini via streamGenerateContent."""
        temp = self.temperature if temperature is None else temperature
        sys_inst, contents = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temp},
        }
        if sys_inst:
            payload["systemInstruction"] = {"parts": [{"text": sys_inst}]}

        url = f"{self.base_url}/{self.model_name}:streamGenerateContent?key={self.api_key}&alt=sse"

        for attempt in range(4):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream("POST", url, json=payload) as stream:
                        if stream.status_code in (400, 401, 403):
                            yield "Gemini authentication failed: Please verify your Google Gemini API key."
                            return
                        if stream.status_code in (503, 429) and attempt < 3:
                            await asyncio.sleep(1.0 * (attempt + 1))
                            continue
                        if stream.status_code != 200:
                            err_body = await stream.aread()
                            err_msg = ""
                            try:
                                err_data = json.loads(err_body.decode("utf-8", errors="replace"))
                                err_msg = err_data.get("error", {}).get("message", "")
                            except Exception:
                                pass  # nosec B110
                            if stream.status_code == 429:
                                yield "⚠️ Google Gemini Rate Limit (HTTP 429): Free tier limit of 5 requests/minute reached. Please wait ~30 seconds for the quota window to reset, or check your quota at https://ai.google.dev."
                                return
                            yield f"Gemini API returned HTTP {stream.status_code}: {err_msg or 'Request failed'}."
                            return

                        async for line in stream.aiter_lines():
                            if not line or not line.startswith("data: "):
                                continue
                            data_str = line[6:].strip()
                            try:
                                data = json.loads(data_str)
                                candidates = data.get("candidates", [])
                                if candidates:
                                    parts = (
                                        candidates[0]
                                        .get("content", {})
                                        .get("parts", [])
                                    )
                                    for part in parts:
                                        text = part.get("text", "")
                                        if text:
                                            yield text
                            except json.JSONDecodeError:
                                continue
                        return
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if attempt < 2:
                    await asyncio.sleep(0.6)
                    continue
                yield "Cannot connect to Gemini API endpoint. Please check your internet connection."
                return
            except Exception as e:
                if attempt < 2:
                    await asyncio.sleep(0.6)
                    continue
                yield f"Gemini error: {e}"
                return

    async def generate(
        self,
        prompt: str,
        temperature: float | None = None,
    ) -> str:
        """Generates a non-streaming response for a prompt string."""
        temp = self.temperature if temperature is None else temperature
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temp},
        }

        url = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"

        for attempt in range(4):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code in (503, 429) and attempt < 3:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    res.raise_for_status()
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        return "".join(p.get("text", "") for p in parts).strip()
                    return ""
            except Exception as e:
                if attempt < 3:
                    await asyncio.sleep(1.0)
                    continue
                return f"[Error from Gemini: {e}]"
        return ""


    async def extract_triples(self, text: str) -> list[dict[str, str]]:
        """Extracts relational triples using Gemini structured prompting."""
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
        """Decides multi-tool routing using Gemini reasoning."""
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
            raw_text = await self.generate(tool_prompt, temperature=0.0)
            if not raw_text or raw_text.startswith("[Error from Gemini:"):
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
