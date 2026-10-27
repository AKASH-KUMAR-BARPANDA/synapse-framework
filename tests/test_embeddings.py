"""Test suite for pluggable embedding models in Synapse."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document

# 1. Test PascalCase and lowercase imports as requested by the user
from Synapse import BaseApp
from Synapse.database import chromadb, in_memory, qdrant
from Synapse.embeddings import minilm, resolve_embedding
from Synapse.models import OllamaModel
from Synapse.resource import Resource
from Synapse.storage import vectorStorage


def test_embedding_resolution():
    print("[1] Testing embedding resolution and factories...")
    # Default BGE FastEmbed
    emb_default = resolve_embedding()
    assert emb_default is not None
    vec_def = emb_default.embed_query("testing default embedding")
    assert len(vec_def) == 384

    # MiniLM via shorthand string
    emb_minilm = resolve_embedding("minilm")
    assert emb_minilm is not None
    vec_mini = emb_minilm.embed_query("testing minilm embedding")
    assert len(vec_mini) == 384

    # MiniLM factory function
    emb_factory = minilm()
    assert emb_factory is not None
    vec_fac = emb_factory.embed_query("testing minilm factory")
    assert len(vec_fac) == 384

    # Custom callable / mock embedding
    class MockCustomEmbedding:
        def embed_documents(self, texts):
            return [[0.1, 0.2, 0.3] for _ in texts]

        def embed_query(self, text):
            return [0.1, 0.2, 0.3]

    mock_emb = MockCustomEmbedding()
    resolved_mock = resolve_embedding(mock_emb)
    assert resolved_mock is mock_emb
    assert resolved_mock.embed_query("test") == [0.1, 0.2, 0.3]
    print("    ✓ Embedding resolution works for defaults, MiniLM, and custom objects!")


def test_chroma_with_minilm():
    print("[2] Testing ChromaDB with MiniLM embeddings...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "chroma_minilm"

        # Developer passes embedding="minilm"
        db = chromadb(path=db_path, embedding="minilm")
        storage = vectorStorage(database=db)

        docs = [
            Document(page_content="Synapse supports pluggable MiniLM ONNX embeddings.", metadata={"source": "test"}),
            Document(page_content="Apples and bananas are nutritious fruits.", metadata={"source": "food"}),
        ]
        storage.add_documents(docs)
        assert storage.count() == 2

        results = storage.similarity_search("MiniLM embedding models", k=1)
        assert len(results) == 1
        assert "MiniLM" in results[0].page_content
        print("    ✓ ChromaDB with MiniLM embedding verified!")


def test_qdrant_with_minilm_and_fastembed():
    print("[3] Testing QdrantDB with MiniLM and FastEmbed embeddings...")
    # Qdrant in-memory with MiniLM
    q_mini = qdrant(location=":memory:", embedding="minilm")
    docs = [
        Document(page_content="Qdrant vector engine running with MiniLM.", metadata={"engine": "qdrant"}),
    ]
    q_mini.add_documents(docs)
    assert q_mini.count() == 1

    search_res = q_mini.similarity_search("Qdrant engine", k=1)
    assert len(search_res) == 1
    assert "Qdrant" in search_res[0].page_content

    # Qdrant in-memory with FastEmbed BGE
    q_bge = qdrant(location=":memory:", embedding="fastembed")
    q_bge.add_documents([Document(page_content="Qdrant with BGE embeddings.", metadata={})])
    assert q_bge.count() == 1
    print("    ✓ Qdrant with MiniLM and FastEmbed embeddings verified!")


def test_in_memory_db_with_minilm():
    print("[4] Testing InMemoryDB with MiniLM embeddings...")
    mem_db = in_memory(embedding="minilm")
    mem_db.add_documents([
        Document(page_content="Ephemeral RAM storage running MiniLM vectors.", metadata={"id": "ram"}),
    ])
    assert mem_db.count() == 1

    matches = mem_db.similarity_search("RAM vectors", k=1)
    assert len(matches) == 1
    assert "MiniLM" in matches[0].page_content
    print("    ✓ InMemoryDB with MiniLM embedding verified!")


def test_base_app_with_custom_embedding():
    print("[5] Testing BaseApp integration with MiniLM vector storage...")
    storage = vectorStorage(database=in_memory(embedding="minilm"))

    app = BaseApp(
        title="MiniLM Intelligence",
        model=OllamaModel(),
        persistent_storage=storage,
    )

    res = Resource("minilm_resource")
    res.add("MiniLM produces compact 384-dimensional vectors with high performance.")
    app.add_resource(res)

    assert app.vector_store.count() == 1
    results = app.vector_store.similarity_search("compact vectors", k=1)
    assert len(results) == 1
    assert "384-dimensional" in results[0].page_content
    print("    ✓ BaseApp integration with MiniLM storage verified!")


if __name__ == "__main__":
    test_embedding_resolution()
    test_chroma_with_minilm()
    test_qdrant_with_minilm_and_fastembed()
    test_in_memory_db_with_minilm()
    test_base_app_with_custom_embedding()
    print("\n🎉 ALL EMBEDDING TESTS PASSED!")
