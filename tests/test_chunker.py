# tests/test_chunker.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from synapse.rag.chunker import DocumentChunker

def test_chunking():
    chunker = DocumentChunker(chunk_size=160, chunk_overlap=30)

    # 1. Test Email Chunking
    sample_email = {
        "id": "msg_8912",
        "subject": "Synapse Architecture Review",
        "from": "sarah@tech.org",
        "to": "dev@synapse.ai",
        "date": "2026-10-08",
        "body": (
            "Hey team, I reviewed the knowledge graph implementation. "
            "We should ensure the MCP client can fetch live email threads "
            "and extract triples in the background without blocking the UI thread. "
            "Let us sync tomorrow at 10 AM to finalize the Ollama prompt routing."
        )
    }

    chunks = chunker.chunk_email(sample_email)
    print(f"Total chunks created: {len(chunks)}")
    for i, doc in enumerate(chunks):
        print(f"\n--- Chunk {i} [{doc.metadata['chunk_id']}] ---")
        print(doc.page_content)
        print("Metadata:", doc.metadata)

if __name__ == "__main__":
    test_chunking()