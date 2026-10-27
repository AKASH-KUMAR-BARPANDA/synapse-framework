# tests/test_rag.py
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from synapse.rag import HybridRAGEngine
from synapse.storage import LocalVectorStorage, PersistentGraphStore
from langchain_core.documents import Document


def test_hybrid_retrieval():
    with tempfile.TemporaryDirectory() as tmpdir:
        v_store = LocalVectorStorage(persist_directory=str(Path(tmpdir) / "chroma"))
        g_store = PersistentGraphStore(filepath=str(Path(tmpdir) / "graph.json"))

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

        assert "entities_detected" in result
        assert "graph_facts" in result
        assert "vector_documents" in result
        assert "formatted_context" in result


if __name__ == "__main__":
    test_hybrid_retrieval()
    print("✓ Hybrid RAG tests passed!")
