# app/config.py
import os
from pathlib import Path

# ===========================================================================
# 1. Base Project Paths
# ===========================================================================
# Points to the root directory ('synapse/') regardless of where Python runs
ROOT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = ROOT_DIR  # Alias for backward-compatible imports

# Storage directory for local binary databases and persistent graph state
DATA_DIR = ROOT_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
GRAPH_FILE = DATA_DIR / "graph.json"

# External authentication credentials for connectors (stored in connectors/)
CONNECTORS_DIR = ROOT_DIR / "connectors"
GMAIL_CREDENTIALS_FILE = CONNECTORS_DIR / "credentials.json"
GMAIL_TOKEN_FILE = CONNECTORS_DIR / "token.json"

# Notion API token (read from environment or .env)
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")

# Automatically create data directories on launch if they do not exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)


# ===========================================================================
# 2. Local LLM Settings (Optimized for Mac 8 GB RAM)
# ===========================================================================
# Default local Ollama host
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Lightweight model with strong instruction-following and ~1 GB RAM footprint
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
LLM_MODEL_NAME = OLLAMA_MODEL  # Backward-compatible alias

# Low temperature ensures factual and consistent entity/graph parsing
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))


# ===========================================================================
# 3. Local Embeddings Settings (FastEmbed / ONNX)
# ===========================================================================
# BAAI/bge-small-en-v1.5 runs via FastEmbed (ONNX runtime)
# Uses ~130 MB RAM on CPU with zero heavy PyTorch overhead
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")


# ===========================================================================
# 4. Text Chunking Parameters (LangChain)
# ===========================================================================
# Compact chunks (~250-280 tokens) work best with small-context local models
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "280"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "30"))


# ===========================================================================
# 5. ChromaDB Vector Collection Settings
# ===========================================================================
CHROMA_COLLECTION_NAME = "synapse_memory"
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "3"))


# ==============================================================================
# 6. SYNAPSE DESIGN SYSTEM: SOLID MATTE SPECIFICATION
# Perceptually calibrated swatches, solid surfaces, zero artificial glow.
# ==============================================================================
DESIGN_TOKENS = {
    "surface": {
        "canvas": "#09090b",       # Zinc 950 (Canvas background)
        "panel": "#18181b",        # Zinc 900 (Solid cards & controls)
        "panel_hover": "#27272a",  # Zinc 800 (Interactive hover)
        "inset": "#121215",        # Zinc 925 (Sunken inputs)
    },
    "border": {
        "subtle": "#27272a",       # Zinc 800 (Hairline 1px border)
        "strong": "#3f3f46",       # Zinc 700 (Focus ring border)
    },
    "text": {
        "primary": "#f4f4f5",      # Zinc 100
        "secondary": "#a1a1aa",    # Zinc 400
        "muted": "#71717a",        # Zinc 500
        "font_family": "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
    },
    "palettes": {
        # Direction B: Linear / Neutral Zinc (Default baseline)
        "zinc": {
            "Person": "#8b8cf8",   # Slate Lavender
            "Email": "#4a9eba",    # Cerulean Gray
            "Project": "#43a077",  # Muted Emerald
            "Tool": "#c98a3e",     # Muted Amber
            "Topic": "#b8607a",    # Steel Rose
            "Default": "#71717a"   # Neutral Slate
        },
        # Direction A: Anthropic / Warm Stone
        "stone": {
            "Person": "#c87a5b",   # Terracotta
            "Email": "#6b8fa3",    # Warm Slate Blue
            "Project": "#769371",  # Olive Sage
            "Tool": "#b8974a",     # Mustard Ochre
            "Topic": "#a4778b",    # Dusty Mauve
            "Default": "#78716c"   # Warm Gray
        },
        # Direction C: Basalt / Industrial Slate
        "basalt": {
            "Person": "#7e74ad",   # Nordic Purple
            "Email": "#5285aa",    # Arctic Denim
            "Project": "#4e9177",  # Spruce Green
            "Tool": "#ba8b4f",     # Raw Brass
            "Topic": "#b05d5d",    # Terracotta Red
            "Default": "#64748b"   # Cool Slate
        }
    },
    "material": {
        "roughness": 0.85,         # Chalky matte surface, no specular plastic shine
        "metalness": 0.05,         # Completely non-reflective
    }
}