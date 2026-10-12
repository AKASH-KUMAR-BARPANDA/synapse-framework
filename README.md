<p align="center">
  <img src="assets/logo.png" width="160" height="160" alt="Synapse Logo" style="border-radius: 36px; box-shadow: 0 12px 36px rgba(0,0,0,0.4);"/>
</p>

<h1 align="center">Synapse</h1>

<p align="center">
  <b>Modular Multi-MCP & Hybrid RAG AI Application Framework</b>
</p>

<p align="center">
  <a href="https://pypi.org/project/synapse-framework/"><img src="https://img.shields.io/pypi/v/synapse-framework.svg?color=6366F1&label=PyPI" alt="PyPI version"/></a>
  <a href="https://pypi.org/project/synapse-framework/"><img src="https://img.shields.io/pypi/pyversions/synapse-framework.svg?color=06B6D4" alt="Python Versions"/></a>
  <a href="https://github.com/AKASH-KUMAR-BARPANDA/synapse-framework/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"/></a>
  <a href="https://github.com/AKASH-KUMAR-BARPANDA/synapse-framework/actions"><img src="https://img.shields.io/badge/tests-23%20passing-success.svg?color=10B981" alt="Tests"/></a>
  <a href="https://github.com/PyCQA/bandit"><img src="https://img.shields.io/badge/security-bandit%20passed-success.svg?color=10B981" alt="Bandit Security"/></a>
</p>

<p align="center">
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-key-features">Features</a> •
  <a href="#-interactive-inspector--3d-graph">Inspector & Graph</a> •
  <a href="#-core-architecture">Architecture</a> •
  <a href="#-api-endpoint-reference">API Endpoints</a> •
  <a href="#-claude-desktop--cursor-export">MCP Export</a> •
  <a href="#-license">License</a>
</p>

---

**Synapse** is an open-source, local-first Python framework for developing autonomous AI assistants, multi-tool agents, and intelligent backend services. It unifies **Model Context Protocol (MCP)** tool execution, **Hybrid RAG** (vector embeddings combined with directed knowledge graphs), pluggable inference providers (**Ollama**, **Google Gemini**, **OpenAI**), and a real-time developer inspector with an interactive 3D WebGL knowledge visualizer.

---

## ⚡ Key Features

- 🔌 **Dynamic Multi-MCP Tool Orchestration** — Aggregate custom Python functions, external FastMCP servers, and cloud services into schema-validated, discoverable tool sets with automatic LLM tool routing.
- 🕸️ **Hybrid RAG (Vector + Knowledge Graph)** — Dual-channel retrieval engine pairing semantic vector search (ChromaDB, Qdrant, FastEmbed) with relation-aware multi-hop graph queries (NetworkX, Neo4j).
- 🧠 **Model Agnostic Inference** — Native support for offline local LLMs via **Ollama** (Qwen 2.5, Llama 3, Mistral) and frontier cloud models (**Google Gemini**, **OpenAI**, Groq, vLLM) with zero lock-in.
- 📊 **Real-Time Interactive Inspector** — Built-in dashboard at `/inspector` to test prompts, monitor live tool execution traces, inspect retrieved vector chunks, and explore relation facts.
- 🌐 **3D WebGL Knowledge Graph** — Standalone interactive visualizer at `/graph/export` featuring physics simulations, entity clustering, and real-time relation navigation.
- 📦 **One-Click MCP Server Export** — Expose your application's tools to Claude Desktop, Cursor, or LibreChat with `synapse export-mcp`.
- 🛡️ **Zero Vulnerabilities & High Test Coverage** — Clean 100% Bandit security audit, full type annotations, and modern Python 3.10+ async architecture.

---

## 📸 Interactive Inspector & 3D Graph

### 1. Developer Inspector Dashboard (`/inspector`)
Test chat prompts, observe schema-validated tool invocations in real time, and audit retrieved vector chunks and knowledge graph triples side-by-side:

<p align="center">
  <img src="assets/inspector_preview.png" width="100%" alt="Synapse Inspector Dashboard" style="border-radius: 12px; border: 1px solid #27272a; box-shadow: 0 8px 24px rgba(0,0,0,0.5);"/>
</p>

### 2. 3D WebGL Knowledge Graph Explorer (`/graph/export`)
Navigate and visualize complex entity relationships and multi-hop triples in an interactive 3D physics-based canvas:

<p align="center">
  <img src="assets/graph_preview.png" width="100%" alt="Synapse 3D Knowledge Graph" style="border-radius: 12px; border: 1px solid #27272a; box-shadow: 0 8px 24px rgba(0,0,0,0.5);"/>
</p>

### 3. Connector & Sync Manager (`/connectors`)
Audit connected tools, check authentication status, and trigger on-demand synchronization:

<p align="center">
  <img src="assets/connectors_preview.png" width="100%" alt="Synapse Connectors View" style="border-radius: 12px; border: 1px solid #27272a; box-shadow: 0 8px 24px rgba(0,0,0,0.5);"/>
</p>

### 4. Interactive OpenAPI & Swagger Endpoints (`/docs`)
Explore and test all REST routes, SSE streams, sync triggers, and MCP export endpoints in real time:

<p align="center">
  <img src="assets/openapi_preview.png" width="100%" alt="Synapse OpenAPI Docs" style="border-radius: 12px; border: 1px solid #27272a; box-shadow: 0 8px 24px rgba(0,0,0,0.5);"/>
</p>

---

## 🏗️ Core Architecture

```mermaid
flowchart TD
    subgraph Clients ["Clients & Interfaces"]
        UI["Web Inspector (/inspector)"]
        CLI["Cursor / Claude Desktop (MCP)"]
        API["REST & SSE Endpoints (/chat)"]
    end

    subgraph Core ["Synapse BaseApp Engine"]
        Router["FastAPI Application"]
        Dispatcher["Tool & Skill Dispatcher"]
        Context["Execution Tracer"]
    end

    subgraph LLM ["Model Providers"]
        OLL["Ollama (Qwen, Llama 3)"]
        GEM["Google Gemini 1.5 / 2.0"]
        OAI["OpenAI (GPT-4o, mini)"]
    end

    subgraph Storage ["Hybrid RAG & Memory"]
        Vec["Vector Store (ChromaDB / Qdrant)"]
        Graph["Knowledge Graph (NetworkX / Neo4j)"]
        Emb["Local Embeddings (FastEmbed / BGE)"]
    end

    subgraph Tools ["Multi-MCP Connectors"]
        F1["Custom Tools (makeconnectors)"]
        F2["OAuth Connectors (Gmail, Notion, Photos)"]
        F3["External FastMCP Servers"]
    end

    UI --> Router
    CLI --> Router
    API --> Router

    Router --> Dispatcher
    Dispatcher <--> LLM
    Dispatcher <--> Storage
    Dispatcher <--> Tools
    Dispatcher --> Context
```

---

## 📦 Installation

Install `synapse-framework` using pip:

```bash
pip install synapse-framework
```

Or using `uv`:

```bash
uv add synapse-framework
```

### Optional Extras

```bash
# Add Qdrant vector database support
pip install "synapse-framework[qdrant]"

# Install all optional drivers and dependencies
pip install "synapse-framework[all]"
```

---

## 🚀 60-Second Quickstart

Create an intelligent assistant with custom Python tools, local Ollama inference, and a live web inspector in under 25 lines of code:

```python
from typing import Dict, Any
from synapse import BaseApp
from synapse.models import Ollama
from synapse.connectors import makeconnectors

# 1. Define custom tools with clear docstrings
def search_product_catalog(query: str, category: str = "all") -> Dict[str, Any]:
    """Searches the product database and inventory across warehouses."""
    return {"results": [{"id": "SKU-992", "name": "Neuro-Link Adapter", "price": 149.0, "stock": 42}]}

def calculate_shipping(weight_kg: float, international: bool = False) -> Dict[str, Any]:
    """Calculates shipping cost based on package weight and destination."""
    rate = 14.5 if international else 5.5
    return {"cost_usd": round(weight_kg * rate, 2), "carrier": "Express Air"}

# 2. Package tools into an MCP connector
inventory_connector = makeconnectors(
    name="inventory_service",
    tools=[search_product_catalog, calculate_shipping],
)

# 3. Initialize Synapse application
app = BaseApp(
    title="Logistics Assistant",
    model=Ollama(model="qwen2.5:0.5b", base_url="http://localhost:11434"),
    connectors=[inventory_connector],
    visualize_graph=True,
)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
```

Open your browser to start interacting:
- 📊 **Web Inspector**: [`http://127.0.0.1:8000/inspector`](http://127.0.0.1:8000/inspector)
- 🕸️ **3D Knowledge Graph**: [`http://127.0.0.1:8000/graph/export`](http://127.0.0.1:8000/graph/export)
- 📖 **Interactive OpenAPI Docs**: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)

---

## 🧠 Pluggable Model Providers

Synapse offers unified model abstractions with automatic prompt formatting and tool calling normalization:

### 1. Local Ollama (Offline / Private)
```python
from synapse.models import Ollama

model = Ollama(
    model="qwen2.5:0.5b",
    base_url="http://localhost:11434",
    temperature=0.2,
)
```

### 2. Google Gemini
```python
import os
from synapse.models import Gemini

model = Gemini(
    api_key=os.getenv("GEMINI_API_KEY"),
    model="gemini-1.5-flash",
)
```

### 3. OpenAI / Groq / OpenRouter / vLLM
```python
import os
from synapse.models import OpenAI

model = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
)
```

---

## 🔌 Connectors & Custom Tools

### Custom Tools via `makeconnectors`
Transform any Python functions into a tool connector ready for MCP client consumption:

```python
from synapse.connectors import makeconnectors

def query_financial_metrics(quarter: str = "Q3") -> dict:
    """Returns quarterly revenue, operating expenses, and net profit margin."""
    return {"revenue": 420000, "expenses": 180000, "margin": "57.1%"}

finance_connector = makeconnectors(
    name="finance_analytics",
    tools=[query_financial_metrics],
)
```

### Prebuilt OAuth Productivity Connectors
Synapse includes managed OAuth 2.0 lifecycle helpers:

```python
from synapse.oauth import GoogleOAuthService
from synapse.connectors import GmailConnectors, GooglePhotosConnectors, NotionConnectors

oauth = GoogleOAuthService(
    credentials_path="credentials.json",
    token_path="token.json",
)

gmail = GmailConnectors(oauth_service=oauth)
photos = GooglePhotosConnectors(oauth_service=oauth)
notion = NotionConnectors(api_key="secret_notion_key")
```

---

## 🕸️ Hybrid RAG & Knowledge Graph

Synapse pairs dense semantic similarity with relational graph reasoning:

```python
from synapse.storage import PersistentGraphStore, VectorStore
from synapse.rag import HybridRAG

# 1. Initialize persistent storage layers
graph_store = PersistentGraphStore(filepath="./data/graph.json")
vector_store = VectorStore(persist_dir="./data/chroma_db")

# 2. Add relational facts to knowledge graph
graph_store.add_relation("Alice", "LEADS", "Platform Engineering", source_type="Person", target_type="Organization")
graph_store.add_relation("Platform Engineering", "MAINTAINS", "Synapse Framework", source_type="Organization", target_type="Project")

# 3. Query combined knowledge base
rag = HybridRAG(vector_store=vector_store, graph_store=graph_store)
result = rag.retrieve_context("What does Alice lead?")

print("Entities found:", result["entities_detected"])
print("Graph facts:", result["graph_facts"])
```

---

## 🌐 API Endpoint Reference

Synapse automatically mounts standard REST, Server-Sent Events (SSE), and documentation endpoints on your application:

| Method | Endpoint | Tag | Description |
| :--- | :--- | :--- | :--- |
| `GET` | **`/`** or **`/inspector`** | `Inspector` | Interactive Web Inspector dashboard for chat, trace inspection, and tools. |
| `POST` | **`/chat`** | `Chat` | Server-Sent Events (SSE) streaming endpoint for agent prompts, tool calls, and grounded replies. |
| `GET` | **`/graph/export`** | `Graph` | Full-screen interactive 3D WebGL knowledge graph visualizer. |
| `GET` | **`/graph/data`** | `Graph` | JSON payload containing all graph nodes, directed links, color tokens, and stats. |
| `GET` | **`/connectors`** | `Sync` | Lists all registered connectors, descriptions, and active tools. |
| `POST` | **`/sync/{connector_name}`** | `Sync` | Triggers background synchronization and indexing for a specific connector. |
| `GET` | **`/sync/status`** | `Sync` | Returns current synchronization progress, item counts, and timestamps. |
| `GET` | **`/mcp/export`** | `MCP` | Exports active tools into Claude Desktop config format and FastMCP manifests. |
| `GET` | **`/skills`** | `Skills` | Returns registered agent skills and specialized system instructions. |
| `GET` | **`/resources`** | `Resources` | Lists static reference documents and indexed data resources. |
| `GET` | **`/info`** | `Inspector` | Overview of running model provider, connector count, and framework version. |
| `GET` | **`/health`** | `System` | Health check endpoint returning status and uptime. |
| `GET` | **`/docs`** | `Docs` | Interactive Swagger / OpenAPI documentation with try-it-out capabilities. |

---

## 🛠️ Claude Desktop & Cursor Export

Export your application tools directly to Claude Desktop or Cursor:

```bash
# Export config file
synapse export-mcp --output claude_desktop_config.json
```

Add the configuration block into your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "synapse": {
      "command": "python",
      "args": ["-m", "synapse.export.mcp_server", "--port", "8000"]
    }
  }
}
```

---

## 🧪 Testing & Code Quality

Synapse is built with strict code quality and security verification:

```bash
# Run pytest test suite (23 unit tests)
pytest tests/

# Run security static analysis (0 vulnerabilities)
bandit -r synapse

# Check code formatting and modern standards
ruff check synapse/
```

---

## 📄 License

Synapse is licensed under the [MIT License](LICENSE).
