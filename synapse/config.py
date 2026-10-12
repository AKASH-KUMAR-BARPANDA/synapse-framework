"""Configuration constants and design tokens for the Synapse framework."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Base filesystem directories (default to working directory or user-specified)
DEFAULT_WORKSPACE_DIR: Path = Path(
    os.getenv("SYNAPSE_WORKSPACE_DIR", Path.cwd())
).resolve()
DEFAULT_DATA_DIR: Path = DEFAULT_WORKSPACE_DIR / "data"
DEFAULT_CHROMA_DIR: Path = DEFAULT_DATA_DIR / "chroma_db"
DEFAULT_GRAPH_FILE: Path = DEFAULT_DATA_DIR / "graph.json"

# Default Model settings
DEFAULT_OLLAMA_BASE_URL: str = os.getenv(
    "OLLAMA_BASE_URL", "http://localhost:11434"
)
DEFAULT_OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
DEFAULT_OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
DEFAULT_TEMPERATURE: float = float(os.getenv("SYNAPSE_TEMPERATURE", "0.1"))

# Embeddings & Chunking
DEFAULT_EMBEDDING_MODEL: str = os.getenv(
    "SYNAPSE_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
)
DEFAULT_CHUNK_SIZE: int = int(os.getenv("SYNAPSE_CHUNK_SIZE", "280"))
DEFAULT_CHUNK_OVERLAP: int = int(os.getenv("SYNAPSE_CHUNK_OVERLAP", "30"))
DEFAULT_CHROMA_COLLECTION: str = "synapse_memory"
DEFAULT_TOP_K: int = int(os.getenv("SYNAPSE_TOP_K", "3"))

# Design Tokens: Solid Matte / Zinc Specification
DESIGN_TOKENS: dict[str, Any] = {
    "surface": {
        "canvas": "#09090b",  # Zinc 950
        "panel": "#18181b",  # Zinc 900
        "panel_hover": "#27272a",  # Zinc 800
        "inset": "#121215",  # Zinc 925
    },
    "border": {
        "subtle": "#27272a",  # Zinc 800
        "strong": "#3f3f46",  # Zinc 700
    },
    "text": {
        "primary": "#f4f4f5",  # Zinc 100
        "secondary": "#a1a1aa",  # Zinc 400
        "muted": "#71717a",  # Zinc 500
        "font_family": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    },
    "palettes": {
        "zinc": {
            "Person": "#818cf8",
            "Email": "#38bdf8",
            "Project": "#34d399",
            "Tool": "#fbbf24",
            "Topic": "#f472b6",
            "Database": "#fb923c",
            "Resource": "#a78bfa",
            "Document": "#60a5fa",
            "Framework": "#2dd4bf",
            "Default": "#94a3b8",
        },
        "stone": {
            "Person": "#e07a5f",
            "Email": "#81b29a",
            "Project": "#f2cc8f",
            "Tool": "#d4a373",
            "Topic": "#b5838d",
            "Database": "#e76f51",
            "Resource": "#6d6875",
            "Document": "#a8dadc",
            "Framework": "#588157",
            "Default": "#a8a29e",
        },
        "basalt": {
            "Person": "#93c5fd",
            "Email": "#67e8f9",
            "Project": "#6ee7b7",
            "Tool": "#fdba74",
            "Topic": "#f9a8d4",
            "Database": "#fca5a5",
            "Resource": "#c4b5fd",
            "Document": "#7dd3fc",
            "Framework": "#14b8a6",
            "Default": "#cbd5e1",
        },
        "neon": {
            "Person": "#00f5d4",
            "Email": "#00bbf9",
            "Project": "#7b2cbf",
            "Tool": "#fee440",
            "Topic": "#f72585",
            "Database": "#ff0054",
            "Resource": "#9b5de5",
            "Document": "#3a86ff",
            "Framework": "#06d6a0",
            "Default": "#00f0ff",
        },
    },
}
