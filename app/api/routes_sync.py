
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from app.core.mcp_client import mcp_manager
from app.core.chunker import DocumentChunker
from app.storage.vector_store import LocalVectorStorage
from app.storage.graph_store import PersistentGraphStore
from app.llm.ollama_client import OllamaClient

router = APIRouter(prefix="/sync", tags=["Sync"])

chunker = DocumentChunker()
vector_store = LocalVectorStorage()
graph_store = PersistentGraphStore()
ollama_client = OllamaClient()


sync_state = {
    "is_syncing": False,
    "source": None,
    "progress": "",
    "items_synced": 0,
    "last_synced_at": None,
    "error": None
}


class SyncGmailRequest(BaseModel):
    query: str = "label:INBOX"
    max_results: int = 5
    extract_graph: bool = True


async def fetch_and_index_gmail(
    query: str = "label:INBOX",
    max_results: int = 5,
    extract_graph: bool = False,
) -> list[Dict[str, Any]]:
    """
    Calls the Gmail MCP `search_emails` tool, indexes the returned emails into
    ChromaDB (`vector_store`) and NetworkX (`graph_store`), updates `sync_state`,
    and returns the fetched email dicts.
    """
    global sync_state
    sync_state["is_syncing"] = True
    sync_state["source"] = "gmail"
    sync_state["progress"] = f"Calling Gmail MCP tool (search_emails: '{query}')..."
    sync_state["error"] = None

    try:
        emails = await mcp_manager.call_tool(
            server_name="gmail",
            tool_name="search_emails",
            arguments={"query": query, "max_results": max_results}
        )

        if not isinstance(emails, list):
            emails = []

        total = len(emails)
        sync_state["progress"] = f"Indexing {total} fetched email(s) into ChromaDB & Knowledge Graph..."

        for idx, email in enumerate(emails, start=1):
            if not isinstance(email, dict):
                continue

            docs = chunker.chunk_email(email)
            if docs:
                vector_store.add_documents(docs)

            sender = email.get("sender", "Unknown Sender")
            subject = email.get("subject", "No Subject")
            graph_store.add_relation(
                source=sender,
                relation="SENT",
                target=subject,
                source_type="Person",
                target_type="Email",
                metadata={
                    "date": email.get("date", ""),
                    "is_unread": bool(email.get("is_unread", False)),
                }
            )

            body_text = email.get("body", "")
            if extract_graph and body_text:
                triples = await ollama_client.extract_triples(body_text[:1200])
                for t in triples:
                    graph_store.add_relation(
                        source=t["source"],
                        relation=t["relation"],
                        target=t["target"],
                        source_type=t.get("source_type", "Default"),
                        target_type=t.get("target_type", "Default")
                    )

            sync_state["progress"] = f"Indexed {idx} of {total} emails..."

        try:
            sync_state["items_synced"] = max(sync_state.get("items_synced", 0), vector_store.count())
        except Exception:
            sync_state["items_synced"] += total
        sync_state["last_synced_at"] = datetime.now(timezone.utc).isoformat()
        sync_state["progress"] = "Sync completed successfully."
        return [e for e in emails if isinstance(e, dict)]

    except Exception as e:
        sync_state["error"] = str(e)
        sync_state["progress"] = "Sync failed."
        raise
    finally:
        sync_state["is_syncing"] = False


async def _process_gmail_sync(query: str, max_results: int, extract_graph: bool):
    try:
        await fetch_and_index_gmail(
            query=query,
            max_results=max_results,
            extract_graph=extract_graph,
        )
    except Exception:
        pass



@router.post("/gmail")
async def trigger_sync_gmail(req: SyncGmailRequest, background_tasks: BackgroundTasks):

    if sync_state["is_syncing"]:
        return {"status": "busy", "message": "A sync is already in progress.", "state": sync_state}

    background_tasks.add_task(
        _process_gmail_sync,
        query=req.query,
        max_results=req.max_results,
        extract_graph=req.extract_graph
    )
    return {"status": "started", "message": "Background sync initiated."}


@router.get("/status")
def get_sync_status() -> Dict[str, Any]:

    return sync_state