# tests/test_graph.py
import sys
import random
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.storage.graph_store import PersistentGraphStore
from app.storage.graph_exporter import GraphExporter

def populate_mock_knowledge_graph():
    # 1. Initialize store (fresh DiGraph for clean visual preview)
    store = PersistentGraphStore()
    store.graph.clear()  # Clear existing items for a crisp benchmark test

    # 2. Base Core Hubs
    store.add_relation("Akash", "CREATOR_OF", "Synapse", source_type="Person", target_type="Project")
    store.add_relation("Synapse", "USES", "ChromaDB", source_type="Project", target_type="Tool")
    store.add_relation("Synapse", "USES", "FastEmbed", source_type="Project", target_type="Tool")
    store.add_relation("Synapse", "USES", "NetworkX", source_type="Project", target_type="Tool")
    store.add_relation("Synapse", "POWERED_BY", "Qwen 3.5 0.8B", source_type="Project", target_type="Tool")

    # 3. Entities Pool (~60+ realistic nodes)
    people = [
        "Sarah Chen", "Dr. Rao", "Marcus Vance", "Elena Rostova", "Rohan Sharma",
        "Priya Patel", "Devin AI", "Alex Rivera", "David Miller", "Kavita Rao"
    ]
    projects = [
        "Synapse", "Neural Search Engine", "Agentic Workflow", "Graph Memory",
        "Edge Inference", "Local RAG Platform", "Smart Inbox"
    ]
    tools = [
        "ChromaDB", "FastEmbed", "NetworkX", "Qwen 3.5 0.8B", "Ollama", "FastMCP",
        "Docker", "PyTorch", "ONNX Runtime", "FastAPI", "SQLite", "Electron", "WebGL"
    ]
    topics = [
        "Vector Embeddings", "Directed Graphs", "Quantization", "MIME Parsing",
        "Apple Silicon Metal", "MCP Protocol", "OAuth 2.0", "Knowledge Extraction",
        "Context Windows", "Zero-Shot Classification", "Semantic Retrieval"
    ]
    emails = [
        "Q3 Project Roadmap", "Sync on Agent Architecture", "API Quota Alert",
        "Weekly AI Digest", "Interview Schedule", "Security Credentials Reset",
        "Conference CFP: Edge AI", "FastMCP Release v0.4", "Invoice #8821"
    ]

    # Node Type Mapping
    type_map = {}
    for p in people: type_map[p] = "Person"
    for pr in projects: type_map[pr] = "Project"
    for t in tools: type_map[t] = "Tool"
    for tp in topics: type_map[tp] = "Topic"
    for e in emails: type_map[e] = "Email"
    type_map["Akash"] = "Person"

    # Predicate Pools
    people_relations = ["DISCUSSED", "COLLABORATES_WITH", "SENT_MESSAGE_TO", "MENTIONED_IN"]
    project_relations = ["DEPENDS_ON", "IMPLEMENTS", "OPTIMIZED_FOR", "EXTENDS"]
    email_relations = ["COVERS_TOPIC", "REFERENCES_PROJECT", "ASSIGNED_TO"]

    # 4. Generate Structured Interconnections
    
    # Connect people to projects and topics
    for person in people:
        store.add_relation("Akash", "COMMUNICATED_WITH", person, "Person", "Person")
        proj = random.choice(projects)
        store.add_relation(person, "CONTRIBUTES_TO", proj, "Person", "Project")
        topic = random.choice(topics)
        store.add_relation(person, random.choice(people_relations), topic, "Person", "Topic")

    # Connect tools to projects and topics
    for tool in tools:
        proj = random.choice(projects)
        topic = random.choice(topics)
        store.add_relation(proj, "USES_LIBRARY", tool, "Project", "Tool")
        store.add_relation(tool, "ENABLES", topic, "Tool", "Topic")

    # Connect emails to entities
    for email in emails:
        sender = random.choice(people)
        proj = random.choice(projects)
        topic = random.choice(topics)
        store.add_relation(sender, "SENT_EMAIL", email, "Person", "Email")
        store.add_relation(email, "RELATES_TO", proj, "Email", "Project")
        store.add_relation(email, "DISCUSSES", topic, "Email", "Topic")

    # Connect topics to other topics (clustering)
    for _ in range(12):
        t1, t2 = random.sample(topics, 2)
        store.add_relation(t1, "ASSOCIATED_WITH", t2, "Topic", "Topic")

    # 5. Export to HTML and Print Stats
    stats = store.get_stats()
    print(f"Generated Graph: {stats['total_nodes']} Nodes, {stats['total_edges']} Edges")

    html_path = GraphExporter.export_to_html(store, "data/graph_preview.html")
    print(f"Obsidian 3D Galaxy saved at: {html_path}")

if __name__ == "__main__":
    populate_mock_knowledge_graph()