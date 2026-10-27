"""Core application orchestrator and framework runner for Synapse."""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections.abc import AsyncGenerator, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.documents import Document
from pydantic import BaseModel, Field

from synapse.config import DEFAULT_DATA_DIR
from synapse.connectors.base import BaseConnector
from synapse.connectors.gmail import GmailConnector
from synapse.database.base import BaseVectorDB
from synapse.database.chroma import chromadb
from synapse.export.mcp_exporter import MCPExporter
from synapse.graph.base import BaseGraphStore
from synapse.graph.networkx_store import networkx
from synapse.inspector.template import render_inspector_html
from synapse.models.base import BaseModelProvider
from synapse.models.ollama import OllamaModel
from synapse.rag.hybrid_rag import HybridRAGEngine
from synapse.resource.resource import Resource
from synapse.skills.skill import Skill, load_premade_skill, makeskills
from synapse.storage.graph_exporter import GraphExporter
from synapse.storage.vector_store import VectorStorage
from synapse.telemetry.mlflow_tracker import MLflowTracker


class ChatMessagePayload(BaseModel):
    """Schema for individual conversation turns."""

    role: str = Field(..., description="Role: 'user', 'assistant', or 'system'.")
    content: str = Field(..., description="Message text content.")


class ChatRequestPayload(BaseModel):
    """Schema for POST /chat request bodies."""

    message: str = Field(..., description="User prompt string.")
    history: list[ChatMessagePayload] | None = Field(
        default_factory=list, description="Conversation history."
    )
    use_rag: bool = Field(
        default=True, description="Enable Hybrid RAG and Multi-MCP tool calls."
    )


class SyncRequestPayload(BaseModel):
    """Schema for manual connector synchronization."""

    query: str | None = Field(default=None, description="Optional search query filter.")
    max_results: int = Field(default=5, description="Maximum items to index.")
    extract_graph: bool = Field(default=True, description="Extract semantic knowledge graph triples.")
    tool_name: str | None = Field(default=None, description="Optional explicit tool name.")
    arguments: dict[str, Any] | None = Field(default=None, description="Optional tool arguments.")


class BaseApp:
    """The primary Synapse Application class.

    Configures models, connectors, local vector storage, knowledge graphs,
    and mounts the interactive inspector web dashboard.

    Example:
        ```python
        from synapse import BaseApp
        from synapse.models import OllamaModel
        from synapse.connectors import GmailConnector, NotionConnector

        app = BaseApp(
            model=OllamaModel(),
            connectors=[
                GmailConnector(credentials_path="credentials.json"),
                NotionConnector(),
            ],
        )

        if __name__ == "__main__":
            app.run()
        ```
    """

    def __init__(
        self,
        title: str = "Synapse AI",
        description: str = "Multi-MCP & Hybrid RAG Framework",
        version: str = "0.2.4",
        model: BaseModelProvider | None = None,
        connectors: list[BaseConnector] | None = None,
        skills: Skill | Sequence[Skill] | str | Path | None = None,
        resource: Resource | Sequence[Resource] | str | Path | Any | None = None,
        resources: Sequence[Resource] | None = None,
        persistent_storage: VectorStorage | BaseVectorDB | bool | None = None,
        Visualize_graph: BaseGraphStore | bool | None = None,
        vector_store: VectorStorage | BaseVectorDB | bool | None = None,
        graph_store: BaseGraphStore | bool | None = None,
        visualize_graph: BaseGraphStore | bool | None = None,
        data_dir: str | Path | None = None,
        mlflow_tracking: bool = False,
        mlflow_experiment: str | None = None,
        mlflow_tracking_uri: str | None = None,
    ) -> None:
        """Initializes the BaseApp instance.

        Args:
            title: Application title displayed in API docs and inspector.
            description: Application summary string.
            version: Semantic version string.
            model: BaseModelProvider instance (defaults to OllamaModel).
            connectors: List of BaseConnector instances (e.g. GmailConnector, NotionConnector).
            skills: Skill, list of Skills, or path(s) to markdown skill files.
            resource: Resource instance, document(s), or file path(s) to index.
            resources: Optional list of Resource instances.
            persistent_storage: Optional vector storage instance (e.g. vectorStorage(database=chromadb(...)))
                or True for default ChromaDB. Defaults to None (storage disabled, 0 files created).
            Visualize_graph: Optional knowledge graph store (e.g. networkx(...) or neo4j(...))
                or True for default NetworkX graph. Defaults to None (graph disabled, 0 files created).
            vector_store: Alias for persistent_storage.
            graph_store: Alias for Visualize_graph.
            visualize_graph: Lowercase alias for Visualize_graph.
            data_dir: Optional custom storage directory.
            mlflow_tracking: Enables automated MLflow experiment and latency tracking.
            mlflow_experiment: Custom MLflow experiment name.
            mlflow_tracking_uri: Optional remote or local MLflow tracking server URI.
        """
        self.title = title
        self.description = description
        self.version = version

        resolved_data_dir = Path(data_dir or DEFAULT_DATA_DIR)
        self.data_dir = resolved_data_dir

        self.model = model or OllamaModel()

        # Resolve vector store (supports persistent_storage or vector_store)
        storage_arg = persistent_storage if persistent_storage is not None else vector_store
        if isinstance(storage_arg, VectorStorage):
            self.vector_store: VectorStorage | None = storage_arg
        elif isinstance(storage_arg, BaseVectorDB):
            self.vector_store = VectorStorage(database=storage_arg)
        elif storage_arg is True:
            resolved_data_dir.mkdir(parents=True, exist_ok=True)
            self.vector_store = VectorStorage(
                database=chromadb(path=self.data_dir / "chroma_db")
            )
        else:
            self.vector_store = None

        # Resolve graph store (supports Visualize_graph, visualize_graph, or graph_store)
        graph_arg = (
            Visualize_graph
            if Visualize_graph is not None
            else (visualize_graph if visualize_graph is not None else graph_store)
        )
        if isinstance(graph_arg, BaseGraphStore):
            self.graph_store: BaseGraphStore | None = graph_arg
        elif graph_arg is True:
            resolved_data_dir.mkdir(parents=True, exist_ok=True)
            self.graph_store = networkx(filepath=self.data_dir / "graph.json")
        else:
            self.graph_store = None

        if data_dir is not None:
            resolved_data_dir.mkdir(parents=True, exist_ok=True)

        self.rag_engine = HybridRAGEngine(
            vector_store=self.vector_store,
            graph_store=self.graph_store,
        )

        self._connectors: dict[str, BaseConnector] = {}
        for conn in connectors or []:
            self.add_connector(conn)

        self.sync_state: dict[str, Any] = {
            "is_syncing": False,
            "source": None,
            "progress": "",
            "items_synced": 0,
            "last_synced_at": None,
            "error": None,
        }

        self._skills: list[Skill] = []
        if skills is not None:
            if isinstance(skills, (list, tuple)):
                for s in skills:
                    self.add_skill(s)
            else:
                self.add_skill(skills)
        else:
            # Auto-attach premade core skills for instant readiness
            for sk_name in ("rag-analyst", "knowledge-graph", "mcp-orchestrator"):
                try:
                    self.add_skill(load_premade_skill(sk_name))
                except Exception:
                    pass  # nosec B110

        self._resources: list[Resource] = []
        if resource is not None:
            if isinstance(resource, (list, tuple)):
                for r in resource:
                    self.add_resource(r)
            else:
                self.add_resource(resource)

        if resources is not None:
            for r in resources:
                self.add_resource(r)

        # Initialize MLflow experiment tracker
        clean_exp = (mlflow_experiment or f"{self.title.lower().replace(' ', '_')}_eval").strip()
        self.mlflow_tracker = MLflowTracker(
            experiment_name=clean_exp,
            tracking_uri=mlflow_tracking_uri,
            enabled=mlflow_tracking or bool(os.getenv("MLFLOW_TRACKING_URI")),
        )

        self._fastapi_app: FastAPI | None = None

    def add_connector(self, connector: BaseConnector) -> None:
        """Registers a connector into this application."""
        self._connectors[connector.name] = connector

    def get_connector(self, name: str) -> BaseConnector | None:
        """Retrieves a registered connector by name."""
        return self._connectors.get(name)

    def list_connectors(self) -> list[BaseConnector]:
        """Returns all registered connector instances."""
        return list(self._connectors.values())

    @property
    def connectors(self) -> list[BaseConnector]:
        """Returns all registered connector instances."""
        return self.list_connectors()

    def add_skill(self, skill: Skill | str | Path) -> Skill:
        """Registers a Skill into this application."""
        sk = skill if isinstance(skill, Skill) else makeskills(skill)
        self._skills.append(sk)
        return sk

    def list_skills(self) -> list[Skill]:
        """Returns all registered skills."""
        return list(self._skills)

    @property
    def skills(self) -> list[Skill]:
        """Returns all registered skills."""
        return self.list_skills()

    def get_skill(self, name: str) -> Skill | None:
        """Retrieves a registered skill by name."""
        for s in self._skills:
            if s.name.lower() == name.lower():
                return s
        return None

    def add_resource(self, resource: Resource | str | Path | Any) -> Resource:
        """Registers and indexes a Resource into vector storage and knowledge graph."""
        res = resource if isinstance(resource, Resource) else Resource(documents=resource)
        self._resources.append(res)
        res.index_into(self.vector_store, self.graph_store)
        if self.vector_store is not None:
            try:
                self.sync_state["items_synced"] = max(
                    self.sync_state.get("items_synced", 0), self.vector_store.count()
                )
            except Exception:
                pass  # nosec B110
        return res

    def list_resources(self) -> list[Resource]:
        """Returns all registered resource collections."""
        return list(self._resources)

    @property
    def resources(self) -> list[Resource]:
        """Returns all registered resource collections."""
        return self.list_resources()


    def get_resource(self, name: str) -> Resource | None:
        """Retrieves a resource collection by name."""
        for r in self._resources:
            if r.name.lower() == name.lower():
                return r
        return None

    async def execute_tool_and_index(
        self,
        connector_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        extract_graph: bool = False,
    ) -> dict[str, Any]:
        """Executes a connector tool and indexes its results into vector and graph stores if enabled."""
        conn = self.get_connector(connector_name)
        if not conn:
            raise KeyError(f"Connector '{connector_name}' is not registered.")

        args = arguments or {}
        raw_result = await conn.call_tool(tool_name, args)

        records: list[dict[str, Any]] = []
        if isinstance(raw_result, list):
            records = [r for r in raw_result if isinstance(r, dict)]
        elif isinstance(raw_result, dict):
            records = [raw_result]

        formatted_items: list[str] = []
        live_chunks: list[dict[str, Any]] = []
        live_triples: list[str] = []

        all_docs: list[Document] = []
        for idx, rec in enumerate(records, start=1):
            # 1. Collect chunks for batch vector upsert
            if self.vector_store is not None:
                docs = conn.chunk_record(tool_name, rec)
                if docs:
                    all_docs.extend(docs)

            # 2. Format context and graph triple
            summary_line, chunk_meta, triple = conn.format_record(tool_name, rec, index=idx)
            formatted_items.append(summary_line)
            live_chunks.append(chunk_meta)
            live_triples.append(triple)

            # 3. Add triple to knowledge graph (atomic batch without saving on each item)
            if self.graph_store is not None:
                parts = [p.strip() for p in triple.split("->")]
                if len(parts) == 3:
                    src, rel, tgt = parts
                    self.graph_store.add_relation(
                        source=src,
                        relation=rel,
                        target=tgt,
                        metadata={"source": connector_name},
                        auto_save=False,
                    )

            # 4. Optional deep LLM triple extraction
            if extract_graph and self.graph_store is not None:
                body = str(rec.get("body") or rec.get("content") or "")
                if body:
                    deep_triples = await self.model.extract_triples(body[:1200])
                    for t in deep_triples:
                        self.graph_store.add_relation(
                            source=t["source"],
                            relation=t["relation"],
                            target=t["target"],
                            source_type=t.get("source_type", "Default"),
                            target_type=t.get("target_type", "Default"),
                            auto_save=False,
                        )

        # Single atomic batch upsert to vector store
        if self.vector_store is not None and all_docs:
            self.vector_store.add_documents(all_docs)

        # Single atomic graph persistence save
        if self.graph_store is not None and hasattr(self.graph_store, "save"):
            try:
                self.graph_store.save()
            except Exception:
                pass  # nosec B110

        try:
            if self.vector_store is not None:
                self.sync_state["items_synced"] = max(
                    self.sync_state.get("items_synced", 0), self.vector_store.count()
                )
            else:
                self.sync_state["items_synced"] = self.sync_state.get("items_synced", 0) + len(records)
        except Exception:
            self.sync_state["items_synced"] = self.sync_state.get("items_synced", 0) + len(records)

        arg_str = ", ".join(f"{k}='{v}'" for k, v in args.items())
        if formatted_items:
            section_text = (
                f"### LIVE {connector_name.upper()} TOOL RESULTS "
                f"({tool_name}, {arg_str}, {len(records)} item(s)):\n"
                + "\n\n".join(formatted_items)
            )
        else:
            section_text = (
                f"### LIVE {connector_name.upper()} TOOL RESULTS "
                f"({tool_name}, {arg_str}):\n0 matching items found."
            )

        return {
            "connector": connector_name,
            "tool": tool_name,
            "arguments": args,
            "records": records,
            "section_text": section_text,
            "live_chunks": live_chunks,
            "live_triples": live_triples,
        }

    async def route_and_execute(self, user_message: str) -> dict[str, Any]:
        """Routes a prompt to appropriate connector tools and executes them."""
        clean_msg = (user_message or "").strip().lower()
        conversational_greetings = {
            "hi", "hello", "hey", "hola", "greetings", "good morning",
            "good afternoon", "good evening", "how are you", "who are you",
            "what can you do", "which model is this", "which model is getting used",
            "what model is this", "what model is being used", "help", "thanks",
            "thank you", "bye", "goodbye", "test", "ping",
        }
        if clean_msg in conversational_greetings:
            return {
                "tool_calls": [],
                "context_sections": [],
                "live_chunks": [],
                "live_triples": [],
            }

        candidate_tools: list[dict[str, Any]] = []
        fallback_calls: list[dict[str, Any]] = []
        unauthenticated_connectors: list[str] = []
        matching_active_conns: list[BaseConnector] = []

        for conn in self._connectors.values():
            if not conn.matches_intent(user_message):
                continue
            if not conn.is_authenticated():
                unauthenticated_connectors.append(conn.name)
                continue
            matching_active_conns.append(conn)

        if matching_active_conns:
            # Parallel tool list discovery across active connectors
            tool_lists = await asyncio.gather(
                *(conn.list_tools() for conn in matching_active_conns),
                return_exceptions=True,
            )
            for conn, tools in zip(matching_active_conns, tool_lists):
                if isinstance(tools, list):
                    for t in tools:
                        candidate_tools.append({
                            "server": conn.name,
                            "name": t.get("name", conn.default_tool),
                            "description": t.get("description", conn.description),
                            "inputSchema": t.get("inputSchema", {}),
                        })
                if conn.default_tool and conn.intent_regex:
                    fallback_calls.append({
                        "server": conn.name,
                        "tool": conn.default_tool,
                        "arguments": conn.default_args_builder(user_message),
                    })

        unauth_notes: list[str] = []
        for c_name in unauthenticated_connectors:
            unauth_notes.append(
                f"### CONNECTOR STATUS NOTE ({c_name.upper()}):\n"
                f"The user's query relates to '{c_name}', but this connector is not currently authenticated. "
                f"Instruct the user to log in or configure credentials in the application Settings."
            )

        if not candidate_tools:
            return {
                "tool_calls": [],
                "context_sections": unauth_notes,
                "live_chunks": [],
                "live_triples": [],
            }

        decided = await self.model.decide_tool_calls(
            user_message=user_message,
            candidate_tools=candidate_tools,
            fallback_calls=fallback_calls,
        )

        context_sections: list[str] = list(unauth_notes)
        live_chunks: list[dict[str, Any]] = []
        live_triples: list[str] = []
        executed: list[dict[str, Any]] = []

        for call in decided:
            srv = call.get("server", "")
            tl = call.get("tool", "")
            args = dict(call.get("arguments") or {})

            conn = self.get_connector(srv)
            if conn:
                defaults = conn.default_args_builder(user_message)
                for k, v in defaults.items():
                    if k not in args or args[k] in (None, ""):
                        args[k] = v

            try:
                res = await self.execute_tool_and_index(
                    connector_name=srv,
                    tool_name=tl,
                    arguments=args,
                    extract_graph=False,
                )
                context_sections.append(res["section_text"])
                live_chunks.extend(res["live_chunks"])
                live_triples.extend(res["live_triples"])
                executed.append({
                    "server": srv,
                    "tool": tl,
                    "arguments": args,
                    "items_fetched": len(res["records"]),
                })
            except Exception as err:
                context_sections.append(
                    f"### {srv.upper()} NOTE:\nLive fetch ({tl}) error: {err}."
                )

        return {
            "tool_calls": executed,
            "context_sections": context_sections,
            "live_chunks": live_chunks,
            "live_triples": live_triples,
        }

    async def chat_stream(
        self,
        message: str,
        history: list[ChatMessagePayload] | None = None,
        use_rag: bool = True,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Streams a chat response token-by-token with live RAG and tool events."""
        context_sections: list[str] = []
        live_tool_chunks: list[dict[str, Any]] = []
        live_tool_triples: list[str] = []
        executed_tools: list[dict[str, Any]] = []

        # 1. On-demand tool calling
        try:
            batch = await self.route_and_execute(message)
            executed_tools = batch.get("tool_calls", [])
            context_sections.extend(batch.get("context_sections", []))
            live_tool_chunks.extend(batch.get("live_chunks", []))
            live_tool_triples.extend(batch.get("live_triples", []))
        except Exception as e:
            context_sections.append(f"### TOOL ROUTER NOTE:\nError: {e}")

        # 2. Local Hybrid RAG retrieval (run off-thread to keep asyncio event loop responsive)
        if use_rag or live_tool_chunks:
            retrieval = await asyncio.to_thread(self.rag_engine.retrieve_context, message)
            rag_str = retrieval.get("formatted_context", "")
            if rag_str and rag_str != "No relevant past context or graph facts found.":
                context_sections.append(rag_str)

            merged_chunks = list(live_tool_chunks)
            for c in retrieval.get("chunks", []):
                merged_chunks.append(c)

            merged_triples = list(
                dict.fromkeys(live_tool_triples + retrieval.get("graph_triples", []))
            )

            first_call = executed_tools[0] if executed_tools else None
            context_data = {
                "chunks": merged_chunks[:6],
                "graph_triples": merged_triples[:8],
                "entities_detected": retrieval.get("entities_detected", []),
                "tool_called": first_call.get("tool") if first_call else None,
                "tool_calls": executed_tools,
            }
            yield {"type": "context", "data": context_data}

        context_str = (
            "\n\n".join(context_sections)
            if context_sections
            else "No external context required."
        )

        skills_section = ""
        if self._skills:
            skills_block = "\n\n".join(s.format_prompt() for s in self._skills)
            skills_section = (
                f"\n\n=== SPECIALIZED SKILLS & GUIDELINES ===\n"
                f"{skills_block}\n"
                f"========================================"
            )

        system_prompt = (
            f"You are {self.title}, an AI assistant with access to connected tools and knowledge.\n"
            "Use the live tool results, specialized skills, and context below to answer accurately and concisely. "
            "If tools were executed in the context above, confirm their execution and report the results to the user.\n\n"
            f"=== CONTEXT ===\n{context_str}\n==============="
            f"{skills_section}"
        )

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history or []:
            messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": message})

        t_start = time.perf_counter()
        full_tokens: list[str] = []
        async for token in self.model.chat_stream(messages):
            full_tokens.append(token)
            yield {"type": "token", "data": token}

        latency_ms = (time.perf_counter() - t_start) * 1000.0
        if getattr(self, "mlflow_tracker", None) and self.mlflow_tracker.is_available():
            self.mlflow_tracker.log_chat_turn(
                message=message,
                response="".join(full_tokens),
                latency_ms=latency_ms,
                model=getattr(self.model, "model_name", "custom"),
                chunks_retrieved=len(merged_chunks) if "merged_chunks" in locals() else len(live_tool_chunks),
                graph_triples=len(merged_triples) if "merged_triples" in locals() else len(live_tool_triples),
                tools_executed=executed_tools,
            )

        yield {"type": "done", "data": {}}

    async def chat(
        self,
        message: str,
        history: list[ChatMessagePayload] | None = None,
        use_rag: bool = True,
    ) -> str:
        """Executes a complete non-streaming chat turn and returns the response string."""
        buf = []
        async for event in self.chat_stream(message, history, use_rag):
            if event["type"] == "token":
                buf.append(event["data"])
        return "".join(buf)

    @property
    def fastapi_app(self) -> FastAPI:
        """Builds and returns the configured FastAPI server."""
        if self._fastapi_app is not None:
            return self._fastapi_app

        api = FastAPI(
            title=self.title,
            description=self.description,
            version=self.version,
        )

        api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app_ref = self

        # ---------------- Chat Route ----------------
        @api.post("/chat", tags=["Chat"])
        async def chat_route(req: ChatRequestPayload):
            async def event_generator():
                try:
                    async for ev in app_ref.chat_stream(
                        req.message, req.history, req.use_rag
                    ):
                        if ev["type"] == "context":
                            yield f"event: context\ndata: {json.dumps(ev['data'])}\n\n"
                        elif ev["type"] == "token":
                            yield f"event: delta\ndata: {json.dumps({'token': ev['data']})}\n\n"
                        elif ev["type"] == "done":
                            yield "event: done\ndata: {}\n\n"
                except Exception as err:
                    yield f"event: error\ndata: {json.dumps({'stage': 'chat', 'detail': str(err)})}\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        # ---------------- Connectors & Sync Routes ----------------
        @api.get("/sync/servers", tags=["Sync"])
        @api.get("/connectors", tags=["Sync"])
        def list_servers():
            return {
                "servers": [
                    {
                        "name": c.name,
                        "description": c.description,
                        "is_ready": c.is_authenticated(),
                        "default_tool": c.default_tool,
                    }
                    for c in app_ref.list_connectors()
                ]
            }

        @api.get("/sync/status", tags=["Sync"])
        def sync_status():
            return app_ref.sync_state

        @api.post("/sync/{connector_name}", tags=["Sync"])
        async def sync_endpoint(
            connector_name: str,
            req: SyncRequestPayload,
            background_tasks: BackgroundTasks,
        ):
            conn = app_ref.get_connector(connector_name)
            if not conn:
                raise HTTPException(status_code=404, detail=f"Connector '{connector_name}' not found.")

            tool = req.tool_name or conn.default_tool
            if req.arguments:
                args = req.arguments
            elif req.query:
                args = {"query": req.query, "max_results": req.max_results}
            elif connector_name == "gmail":
                args = {"query": "label:INBOX", "max_results": req.max_results}
            else:
                args = {"max_results": req.max_results}

            async def _bg_task():
                app_ref.sync_state["is_syncing"] = True
                app_ref.sync_state["source"] = connector_name
                app_ref.sync_state["progress"] = f"Syncing {connector_name}..."
                try:
                    await app_ref.execute_tool_and_index(
                        connector_name=connector_name,
                        tool_name=tool,
                        arguments=args,
                        extract_graph=req.extract_graph,
                    )
                    app_ref.sync_state["progress"] = "Sync completed successfully."
                    app_ref.sync_state["last_synced_at"] = datetime.now(timezone.utc).isoformat()
                except Exception as err:
                    app_ref.sync_state["error"] = str(err)
                    app_ref.sync_state["progress"] = "Sync failed."
                finally:
                    app_ref.sync_state["is_syncing"] = False

            background_tasks.add_task(_bg_task)
            return {"status": "started", "message": f"Background sync initiated for '{connector_name}'."}

        # ---------------- Auth Routes ----------------
        @api.get("/auth/status", tags=["Auth"])
        def auth_status():
            out = {}
            for c in app_ref.list_connectors():
                has_creds = False
                if hasattr(c, "oauth") and hasattr(c.oauth, "has_credentials"):
                    has_creds = c.oauth.has_credentials()
                elif hasattr(c, "has_credentials"):
                    has_creds = c.has_credentials() if callable(c.has_credentials) else bool(c.has_credentials)
                else:
                    has_creds = c.is_authenticated()

                is_auth = c.is_authenticated()
                if is_auth:
                    status_str = "connected"
                elif has_creds:
                    status_str = "needs_login"
                else:
                    status_str = "unconfigured"

                out[c.name] = {
                    "status": status_str,
                    "has_credentials": bool(has_creds),
                    "is_authenticated": bool(is_auth),
                }
            return out

        @api.post("/auth/gmail/upload-credentials", tags=["Auth"])
        async def upload_creds(file: UploadFile = File(...)):
            content = await file.read()
            gmail_conn = app_ref.get_connector("gmail")
            if isinstance(gmail_conn, GmailConnector):
                saved_path = gmail_conn.oauth.save_credentials(content)
                return {"status": "saved", "path": str(saved_path)}
            return {"status": "error", "message": "Gmail connector not registered."}

        @api.post("/auth/gmail/login", tags=["Auth"])
        def login_gmail_route():
            gmail_conn = app_ref.get_connector("gmail")
            if isinstance(gmail_conn, GmailConnector):
                creds = gmail_conn.oauth.authenticate()
                return {"status": "success", "authenticated": creds.valid}
            return {"status": "error", "message": "Gmail connector not registered."}

        @api.post("/auth/gmail/disconnect", tags=["Auth"])
        def disconnect_gmail_route():
            gmail_conn = app_ref.get_connector("gmail")
            if isinstance(gmail_conn, GmailConnector):
                gmail_conn.oauth.disconnect()
            return {"status": "disconnected"}

        # ---------------- Graph Routes ----------------
        @api.get("/graph/data", tags=["Graph"])
        def graph_data_route():
            palette = {
                "Person": "#a1a1aa",
                "Email": "#e4e4e7",
                "Topic": "#71717a",
                "Organization": "#d4d4d8",
                "Date": "#52525b",
                "Default": "#71717a",
            }
            if app_ref.graph_store is None:
                return {
                    "nodes": [],
                    "links": [],
                    "stats": {"total_nodes": 0, "total_edges": 0},
                    "tokens": {
                        "canvas": "#09090b",
                        "palette": palette,
                    },
                }

            if hasattr(app_ref.graph_store, "load"):
                app_ref.graph_store.load()
            payload = app_ref.graph_store.get_3d_payload()
            stats = (
                app_ref.graph_store.get_stats()
                if hasattr(app_ref.graph_store, "get_stats")
                else {
                    "total_nodes": len(payload.get("nodes", [])),
                    "total_edges": len(payload.get("links", [])),
                }
            )
            return {
                "nodes": payload["nodes"],
                "links": payload["links"],
                "stats": stats,
                "tokens": {
                    "canvas": "#09090b",
                    "palette": palette,
                },
            }

        @api.get("/graph/export", response_class=HTMLResponse, tags=["Graph"])
        def graph_export_route():
            if app_ref.graph_store is None:
                return HTMLResponse(
                    content=(
                        "<html><body style='background:#09090b;color:#e4e4e7;font-family:sans-serif;padding:40px;'>"
                        "<h2>Knowledge Graph Not Configured</h2>"
                        "<p>Provide <code>Visualize_graph=networkx(...)</code> or <code>in_memory_graph()</code> to BaseApp to enable graph visualization.</p>"
                        "</body></html>"
                    )
                )
            html_content = GraphExporter.render_html(app_ref.graph_store)
            try:
                if app_ref.data_dir.exists():
                    export_path = app_ref.data_dir / "graph_preview.html"
                    export_path.write_text(html_content, encoding="utf-8")
            except Exception:
                pass  # nosec B110
            return HTMLResponse(content=html_content)

        # ---------------- MCP Export Route ----------------
        @api.get("/mcp/export", tags=["MCP"])
        def mcp_export_route():
            return {
                "mcpServers": MCPExporter.to_claude_desktop_config(app_ref)["mcpServers"],
                "tools": MCPExporter.to_tools_list(app_ref),
            }

        # ---------------- Inspector Dashboard Route ----------------
        @api.get("/info", tags=["Inspector"])
        def app_info():
            provider = type(app_ref.model).__name__.replace("Model", "")
            m_name = getattr(app_ref.model, "model_name", "Unknown")
            return {
                "title": app_ref.title,
                "version": app_ref.version,
                "model_provider": provider,
                "model_name": m_name,
                "model_display": f"{provider} ({m_name})",
                "connectors_count": len(app_ref._connectors),
                "skills_count": len(app_ref._skills),
                "resources_count": len(app_ref._resources),
            }

        @api.get("/", response_class=HTMLResponse, tags=["Inspector"])
        @api.get("/inspector", response_class=HTMLResponse, tags=["Inspector"])
        def inspector_dashboard():
            provider = type(app_ref.model).__name__.replace("Model", "")
            m_name = getattr(app_ref.model, "model_name", "Unknown")
            model_display = f"{provider} ({m_name})"
            return HTMLResponse(content=render_inspector_html(model_display=model_display))

        # ---------------- Skills & Resources Routes ----------------
        @api.get("/skills", tags=["Skills"])
        def list_skills_route():
            return {"skills": [s.to_dict() for s in app_ref.list_skills()]}

        @api.get("/resources", tags=["Resources"])
        def list_resources_route():
            return {"resources": [r.to_dict() for r in app_ref.list_resources()]}

        # ---------------- Static Previews ----------------
        if self.data_dir.exists():
            api.mount(
                "/preview",
                StaticFiles(directory=str(self.data_dir), html=True),
                name="preview",
            )

        @api.get("/health", tags=["System"])
        async def health_probe():
            provider_type = type(app_ref.model).__name__.replace("Model", "").lower()
            model_status = "unconfigured"

            if provider_type == "ollama":
                base_url = getattr(app_ref.model, "base_url", "http://localhost:11434")
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=0.4) as client:
                        res = await client.get(f"{base_url}/api/tags")
                        model_status = "ready" if res.status_code == 200 else "unreachable"
                except Exception:
                    model_status = "unreachable"
            elif provider_type in ("openai", "gemini"):
                api_key = getattr(app_ref.model, "api_key", None)
                model_status = "ready" if bool(api_key) else "needs_api_key"
            else:
                model_status = "ready"

            gmail_conn = app_ref.get_connector("gmail")
            gmail_ready = gmail_conn.is_authenticated() if gmail_conn else False
            chroma_path = app_ref.data_dir / "chroma_db"

            v_count = 0
            if app_ref.vector_store is not None:
                try:
                    v_count = app_ref.vector_store.count()
                except Exception:
                    v_count = 0

            g_count = 0
            if app_ref.graph_store is not None:
                try:
                    if hasattr(app_ref.graph_store, "graph"):
                        g_count = app_ref.graph_store.graph.number_of_nodes()
                    elif hasattr(app_ref.graph_store, "count_nodes"):
                        g_count = app_ref.graph_store.count_nodes()
                    else:
                        g_count = len(app_ref.graph_store.get_3d_payload().get("nodes", []))
                except Exception:
                    g_count = 0

            storage_status = "disabled"
            if app_ref.vector_store is not None:
                storage_status = "ready" if (chroma_path.exists() or hasattr(app_ref.vector_store, "database")) else "initialized"

            services_dict = {
                provider_type: model_status,
                "chroma_db": storage_status,
                "gmail_connector": "connected" if gmail_ready else "disconnected",
            }

            return {
                "status": "online",
                "app": app_ref.title,
                "version": app_ref.version,
                "model": getattr(app_ref.model, "model_name", "unknown"),
                "model_provider": provider_type,
                "services": services_dict,
                "connectors": [c.name for c in app_ref.list_connectors()],
                "skills": [s.name for s in app_ref.list_skills()],
                "resources": [r.name for r in app_ref.list_resources()],
                "resource_items": sum(len(r.documents) for r in app_ref.list_resources()),
                "mcp_servers": [
                    {"name": c.name, "is_ready": c.is_authenticated()}
                    for c in app_ref.list_connectors()
                ],
                "vector_items": v_count,
                "graph_nodes": g_count,
            }

        self._fastapi_app = api
        return self._fastapi_app

    def to_mcp_server(self, name: str | None = None) -> Any:
        """Converts all registered connectors into an official MCP Server instance."""
        from synapse.export.mcp_exporter import MCPExporter
        return MCPExporter.create_mcp_server(self, name=name or self.title)

    def run_mcp(self, transport: str = "stdio") -> None:
        """Runs all app connectors as an official MCP server over stdio or SSE."""
        server = self.to_mcp_server()
        server.run(transport=transport)

    def run(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        reload: bool = False,
    ) -> None:
        """Launches the Synapse server and interactive web inspector."""
        print(f"\n🚀 Synapse [{self.title}] online at http://{host}:{port}")
        print(f"📊 Interactive Inspector: http://{host}:{port}/inspector")
        print(f"📖 OpenAPI Docs: http://{host}:{port}/docs\n")
        uvicorn.run(self.fastapi_app, host=host, port=port, reload=reload)


# Developer-friendly alias
SynapseApp = BaseApp
