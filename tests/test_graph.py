# tests/test_graph.py
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from synapse.storage import PersistentGraphStore, GraphExporter


def test_knowledge_graph_and_export():
    with tempfile.TemporaryDirectory() as tmpdir:
        graph_path = Path(tmpdir) / "graph.json"
        export_html_path = Path(tmpdir) / "graph.html"

        store = PersistentGraphStore(filepath=str(graph_path))
        store.graph.clear()

        # Add relations
        store.add_relation("Developer", "CREATOR_OF", "Synapse", source_type="Person", target_type="Project")
        store.add_relation("Synapse", "USES", "ChromaDB", source_type="Project", target_type="Tool")
        store.add_relation("Synapse", "USES", "FastEmbed", source_type="Project", target_type="Tool")
        store.add_relation("Synapse", "USES", "NetworkX", source_type="Project", target_type="Tool")

        assert store.graph.number_of_nodes() == 5
        assert store.graph.number_of_edges() == 4

        # Test querying neighbors
        synapse_rels = store.find_relation_for("Synapse")
        assert len(synapse_rels) >= 3

        # Test export to HTML
        GraphExporter.export_to_html(store, str(export_html_path))
        assert export_html_path.exists()
        assert export_html_path.stat().st_size > 0


if __name__ == "__main__":
    test_knowledge_graph_and_export()
    print("✓ Knowledge graph tests passed!")
