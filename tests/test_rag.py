# tests/test_hybrid_rag.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.hybrid_rag import HybridRAGEngine
from app.storage.vector_store import LocalVectorStorage
from app.storage.graph_store import PersistentGraphStore
from langchain_core.documents import Document

def test_hybrid_retrieval():
    v_store = LocalVectorStorage()
    g_store = PersistentGraphStore()

    # 1. Seed sample vector chunk
    v_store.add_documents([
        Document(
            page_content="Sarah Chen sent notes stating Synapse Metal acceleration is fully verified.",
            metadata={"source": "gmail", "subject": "Engine Updates"}
        )
    ])

    # 2. Seed sample graph relations
    g_store.add_relation("Sarah Chen", "LEADS", "Synapse Project", source_type="Person", target_type="Project")
    g_store.add_relation("Synapse Project", "USES", "FastEmbed", source_type="Project", target_type="Tool")

    engine = HybridRAGEngine(vector_store=v_store, graph_store=g_store)

    # 3. Query targeting both vector content and graph entities
    query = "What is Sarah Chen working on?"
    result = engine.retrieve_context(query)

    print("=== HYBRID RETRIEVAL REPORT ===")
    print(f"Entities Detected: {result['entities_detected']}")
    print(f"Graph Facts Found: {len(result['graph_facts'])}")
    print(f"Vector Chunks Found: {len(result['vector_documents'])}")
    print("\n--- Formatted Context for LLM ---")
    print(result["formatted_context"])

if __name__ == "__main__":
    test_hybrid_retrieval()