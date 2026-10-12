
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx

from app.api.routes_sync import router as sync_router
from app.api.routes_chat import router as chat_router
from app.api.routes_auth import router as auth_router
from app.api.routes_graph import router as graph_router
from app.config import DATA_DIR, OLLAMA_BASE_URL, CHROMA_DIR, GMAIL_TOKEN_FILE

app = FastAPI(
    title="Synapse Core API",
    description="Personal AI Assistant",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router)
app.include_router(sync_router)
app.include_router(auth_router)
app.include_router(graph_router)


if DATA_DIR.exists():
    app.mount("/preview", StaticFiles(directory=str(DATA_DIR), html=True), name="preview")


@app.get("/health")
async def health_check():
    ollama_ready = False
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            res = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            ollama_ready = (res.status_code == 200)
    except Exception:
        ollama_ready = False

    return {
        "status": "online",
        "services": {
            "ollama": "ready" if ollama_ready else "unreachable",
            "chroma_db": "ready" if CHROMA_DIR.exists() else "uninitialized",
            "gmail_connector": "connected" if GMAIL_TOKEN_FILE.exists() else "disconnected"
        }
    }