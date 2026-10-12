import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import GMAIL_TOKEN_FILE
from app.storage.vector_store import LocalVectorStorage
from app.storage.graph_store import PersistentGraphStore
from app.core.hybrid_rag import HybridRAGEngine
from app.llm.ollama_client import OllamaClient
from app.api.routes_sync import fetch_and_index_gmail

router = APIRouter(prefix="/chat", tags=["Chat"])

vector_store = LocalVectorStorage()
graph_store = PersistentGraphStore()
rag_engine = HybridRAGEngine(vector_store, graph_store)
ollama_client = OllamaClient()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    use_rag: bool = True


@router.post("")
async def chat_endpoint(req: ChatRequest):
    async def event_generator():
        context_sections: List[str] = []
        live_tool_chunks: List[Dict[str, Any]] = []
        live_tool_triples: List[str] = []
        sources: Dict[str, Any] = {"chunks": [], "graph_triples": []}

        # 1. On-Demand MCP Tool Calling:
        # Let the LLM router decide if this query needs a live Gmail tool call (`search_emails`).
        tool_decision = await ollama_client.decide_gmail_tool_call(req.message)
        if tool_decision and GMAIL_TOKEN_FILE.exists():
            tool_query = tool_decision.get("query", "label:INBOX")
            tool_max_results = int(tool_decision.get("max_results", 5))
            try:
                fetched_emails = await fetch_and_index_gmail(
                    query=tool_query,
                    max_results=tool_max_results,
                    extract_graph=False,
                )
                if fetched_emails:
                    formatted_live_emails = []
                    for idx, em in enumerate(fetched_emails, start=1):
                        unread_badge = "UNREAD" if em.get("is_unread") else "READ"
                        subj = em.get("subject", "No Subject")
                        sender = em.get("sender", "Unknown Sender")
                        date_str = em.get("date", "")
                        body_excerpt = (em.get("body") or em.get("snippet") or "")[:600].strip()

                        formatted_live_emails.append(
                            f"{idx}. [{unread_badge}] Subject: {subj}\n"
                            f"   From: {sender} | Date: {date_str}\n"
                            f"   Content: {body_excerpt}"
                        )
                        live_tool_chunks.append({
                            "page_content": (
                                f"[EMAIL | {unread_badge}] Subject: {subj} | From: {sender}\n"
                                f"Date: {date_str}\n\n{body_excerpt}"
                            ),
                            "metadata": {
                                "source": "gmail_mcp_live",
                                "subject": f"[{unread_badge}] {subj}",
                                "sender": sender,
                                "date": date_str,
                                "is_unread": bool(em.get("is_unread", False)),
                            },
                            "source": "gmail_mcp_live",
                            "subject": f"[{unread_badge}] {subj}",
                            "chunk_id": f"live_{em.get('id', idx)}",
                        })
                        live_tool_triples.append(f"{sender} -> SENT -> {subj}")

                    context_sections.append(
                        f"### LIVE GMAIL MCP TOOL RESULTS (query='{tool_query}', {len(fetched_emails)} message(s) fetched & indexed):\n"
                        + "\n\n".join(formatted_live_emails)
                    )
                else:
                    context_sections.append(
                        f"### LIVE GMAIL MCP TOOL RESULTS (query='{tool_query}'):\n"
                        "0 matching messages were found in Gmail for this query."
                    )
            except Exception as tool_err:
                context_sections.append(
                    f"### GMAIL MCP TOOL NOTE:\nLive Gmail fetch encountered an error ({tool_err}); falling back to locally indexed memory."
                )

        # 2. Local Hybrid RAG Retrieval (ChromaDB Vectors + NetworkX Knowledge Graph)
        if req.use_rag or live_tool_chunks:
            try:
                retrieval = rag_engine.retrieve_context(req.message)
                rag_context_str = retrieval.get("formatted_context", "")
                if rag_context_str and rag_context_str != "No relevant past context or graph facts found.":
                    context_sections.append(rag_context_str)

                rag_chunks = retrieval.get("chunks", [])
                rag_triples = retrieval.get("graph_triples", retrieval.get("graph_facts", []))

                merged_chunks = list(live_tool_chunks)
                seen_subjects = {c.get("subject", "").replace("[UNREAD] ", "").replace("[READ] ", "") for c in merged_chunks}
                for rc in rag_chunks:
                    if rc.get("subject", "") not in seen_subjects:
                        merged_chunks.append(rc)

                merged_triples = list(dict.fromkeys(live_tool_triples + list(rag_triples)))

                sources = {
                    "chunks": merged_chunks[:6],
                    "graph_triples": merged_triples[:8],
                    "entities_detected": retrieval.get("entities_detected", []),
                    "tool_called": tool_decision.get("tool") if tool_decision else None,
                    "tool_query": tool_decision.get("query") if tool_decision else None,
                }

                yield f"event: context\ndata: {json.dumps(sources)}\n\n"
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'stage': 'rag', 'detail': str(e)})}\n\n"

        context_str = (
            "\n\n".join(context_sections)
            if context_sections
            else "No external context required or found for this query."
        )

        system_prompt = (
            "You are Synapse, a private local-first AI assistant with on-demand Gmail MCP tool access.\n"
            "When LIVE GMAIL MCP TOOL RESULTS or CONTEXT are provided below, use them to answer accurately and concisely "
            "(paying attention to [UNREAD] vs [READ] badges, senders, subjects, and dates).\n"
            "If the user is asking a general question that does not require personal context, answer helpful and directly.\n\n"
            f"=== CONTEXT ===\n{context_str}\n==============="
        )

        messages = [{"role": "system", "content": system_prompt}]
        for turn in req.history or []:
            messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": req.message})

        try:
            async for token in ollama_client.chat_stream(messages):
                payload = json.dumps({"token": token})
                yield f"event: delta\ndata: {payload}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'stage': 'llm', 'detail': str(e)})}\n\n"

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )