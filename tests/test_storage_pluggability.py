"""Test suite for pluggable database, storage, and graph backends in Synapse."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document

# Test both PascalCase and lowercase imports as requested by the user
from Synapse import BaseApp
from Synapse.database import chromadb, in_memory, pgvector, qdrant
from Synapse.graph import in_memory_graph, neo4j, networkx
from Synapse.models import OllamaModel
from Synapse.resource import Resource
from Synapse.storage import vectorStorage


def test_import_and_factories():
    print("[1] Testing database, storage, and graph imports and factories...")
    assert callable(chromadb)
    assert callable(in_memory)
    assert callable(qdrant)
    assert callable(pgvector)
    assert callable(vectorStorage)
    assert callable(networkx)
    assert callable(in_memory_graph)
    assert callable(neo4j)
    print("    ✓ All storage and graph factories import cleanly!")


def test_zero_storage_base_app():
    print("[2] Testing zero-storage BaseApp (no vector store, no graph store)...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "test_app_storage"

        app = BaseApp(
            title="Zero Storage App",
            model=OllamaModel(),
            data_dir=tmp_path,
            persistent_storage=None,
            Visualize_graph=None,
        )

        assert app.vector_store is None
        assert app.graph_store is None

        # Verify no chroma_db folder and no graph.json were created
        assert not (tmp_path / "chroma_db").exists()
        assert not (tmp_path / "graph.json").exists()

        # Test FastAPI routes when storage is disabled
        from fastapi.testclient import TestClient

        client = TestClient(app.fastapi_app)

        health_res = client.get("/health")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert health_data["vector_items"] == 0
        assert health_data["graph_nodes"] == 0
        assert health_data["services"]["chroma_db"] == "disabled"

        graph_res = client.get("/graph/data")
        assert graph_res.status_code == 200
        graph_data = graph_res.json()
        assert graph_data["nodes"] == []
        assert graph_data["links"] == []

        export_res = client.get("/graph/export")
        assert export_res.status_code == 200
        assert "Knowledge Graph Not Configured" in export_res.text

        print("    ✓ Zero-storage mode creates 0 disk artifacts and serves graceful fallbacks!")


def test_in_memory_storage_and_graph():
    print("[3] Testing in-memory vector storage & in-memory graph...")
    # Pure RAM vector database: 0 disk files
    mem_db = in_memory()
    storage = vectorStorage(database=mem_db)

    # Pure RAM graph store: 0 disk files
    mem_graph = networkx()  # filepath=None

    app = BaseApp(
        title="In-Memory App",
        model=OllamaModel(),
        persistent_storage=storage,
        Visualize_graph=mem_graph,
    )

    assert app.vector_store is not None
    assert app.graph_store is not None

    # Ingest resources
    res = Resource("developer_docs")
    res.add("FastAPI is a modern, fast web framework for building APIs with Python.")
    res.add("FastMCP provides ergonomic primitives for Model Context Protocol servers.")
    app.add_resource(res)

    assert app.vector_store.count() == 2
    assert app.graph_store.count_nodes() >= 1

    # Perform similarity search
    results = app.vector_store.similarity_search("How to build APIs with Python?", k=1)
    assert len(results) == 1
    assert "FastAPI" in results[0].page_content

    # Query graph
    facts = app.graph_store.find_relation_for("developer_docs")
    assert len(facts) >= 1

    # Test routes
    from fastapi.testclient import TestClient

    client = TestClient(app.fastapi_app)

    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["vector_items"] == 2
    assert health_res.json()["graph_nodes"] >= 1

    graph_res = client.get("/graph/data")
    assert graph_res.status_code == 200
    assert len(graph_res.json()["nodes"]) >= 1

    print("    ✓ In-memory database & graph work seamlessly with 0 disk footprint!")


def test_persistent_storage_configuration():
    print("[4] Testing custom persistent ChromaDB and NetworkX file configuration...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "custom_chroma"
        graph_file = Path(tmp_dir) / "custom_graph.json"

        # Developer configures them explicitly as requested
        custom_db = chromadb(path=db_path)
        storage = vectorStorage(database=custom_db)
        custom_graph = networkx(filepath=graph_file)

        app = BaseApp(
            title="Persistent App",
            model=OllamaModel(),
            persistent_storage=storage,
            Visualize_graph=custom_graph,
        )

        res = Resource("persisted_notes")
        res.add("Synapse delivers modular hybrid RAG intelligence.")
        app.add_resource(res)

        assert app.vector_store.count() == 1
        assert graph_file.exists()
        assert db_path.exists()

        results = app.vector_store.similarity_search("hybrid RAG intelligence", k=1)
        assert len(results) == 1
        assert "Synapse" in results[0].page_content
        print("    ✓ Explicit chromadb() and networkx(filepath=...) persistence verified!")


if __name__ == "__main__":
    test_import_and_factories()
    test_zero_storage_base_app()
    test_in_memory_storage_and_graph()
    test_persistent_storage_configuration()
    print("\n🎉 ALL STORAGE & GRAPH PLUGGABILITY TESTS PASSED!")
