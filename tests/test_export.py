"""Test suite for MCP and Graph exporters in Synapse."""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from Synapse import BaseApp
from Synapse.connectors import makeconnectors
from Synapse.export import GraphExporter, MCPExporter, graphexporter, mcpexporter
from Synapse.graph import networkx
from Synapse.models import OllamaModel


def test_mcp_exporter():
    print("[1] Testing MCPExporter and mcpexporter aliases...")
    assert MCPExporter is not None
    assert mcpexporter is MCPExporter
    assert GraphExporter is not None
    assert graphexporter is GraphExporter

    def lookup_stock(symbol: str = "AAPL"):
        """Fetches latest stock quotes."""
        return [{"symbol": symbol, "price": 220.5}]

    stock_conn = makeconnectors(
        name="finance_tools",
        description="Market and stock valuation tools",
        tools={"lookup_stock": lookup_stock},
    )

    app = BaseApp(
        model=OllamaModel(),
        connectors=[stock_conn],
    )

    tools_list = mcpexporter.to_tools_list(app)
    assert len(tools_list) >= 1
    assert any("lookup_stock" in t["name"] for t in tools_list)

    claude_cfg = mcpexporter.to_claude_desktop_config(app)
    assert "mcpServers" in claude_cfg
    assert "synapse" in claude_cfg["mcpServers"]
    # Check that args target stdio mcp mode
    assert "mcp" in claude_cfg["mcpServers"]["synapse"]["args"]

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = Path(tmp_dir) / "claude_desktop_config.json"
        saved = mcpexporter.save_claude_desktop_config(app, filepath=out_file)
        assert saved.exists()
        parsed = json.loads(saved.read_text(encoding="utf-8"))
        assert "mcpServers" in parsed

    # Test FastAPI /mcp/export endpoint
    client = TestClient(app.fastapi_app)
    res = client.get("/mcp/export")
    assert res.status_code == 200
    export_payload = res.json()
    assert "mcpServers" in export_payload
    assert "tools" in export_payload

    # Test official MCPServer creation from connector and app
    conn_mcp_server = stock_conn.to_mcp_server()
    assert conn_mcp_server is not None

    async def _test_tool_execution():
        result = await conn_mcp_server.call_tool("lookup_stock", {"symbol": "AAPL"})
        assert result is not None
        assert not result.is_error

    asyncio.run(_test_tool_execution())

    app_mcp_server = app.to_mcp_server()
    assert app_mcp_server is not None
    print("    ✓ MCPExporter schemas, Claude Desktop config, MCPServer instance, and tool dispatch verified!")


def test_graph_exporter():
    print("[2] Testing GraphExporter and /graph/export route...")
    from synapse.graph import in_memory_graph, networkx

    # Test 1: InMemoryGraph (BaseGraphStore subclass)
    mem_graph = in_memory_graph()
    mem_graph.add_node("concept_rag", "Topic", color="#3b82f6")
    mem_graph.add_node("concept_mcp", "Tool", color="#10b981")
    mem_graph.add_edge("concept_rag", "concept_mcp", "CONNECTS_TO")

    html_mem = GraphExporter.render_html(mem_graph)
    assert "<!DOCTYPE html>" in html_mem
    assert "concept_rag" in html_mem
    assert "concept_mcp" in html_mem
    assert "3d-force-graph" in html_mem

    # Test 2: NetworkXGraph
    nx_graph = networkx()
    nx_graph.add_node("user_alice", "Person", color="#ec4899")
    nx_graph.add_node("repo_synapse", "Project", color="#f59e0b")
    nx_graph.add_edge("user_alice", "repo_synapse", "CONTRIBUTES_TO")

    html_nx = GraphExporter.render_html(nx_graph)
    assert "<!DOCTYPE html>" in html_nx
    assert "user_alice" in html_nx
    assert "repo_synapse" in html_nx

    # Test 3: BaseApp with Visualize_graph and /graph/export endpoint
    app = BaseApp(
        model=OllamaModel(),
        Visualize_graph=mem_graph,
    )
    client = TestClient(app.fastapi_app)
    res = client.get("/graph/export")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert "concept_rag" in res.text

    # Test 4: BaseApp without graph store
    app_no_graph = BaseApp(model=OllamaModel())
    client_no_graph = TestClient(app_no_graph.fastapi_app)
    res_no_graph = client_no_graph.get("/graph/export")
    assert res_no_graph.status_code == 200
    assert "Knowledge Graph Not Configured" in res_no_graph.text

    print("    ✓ GraphExporter HTML rendering and /graph/export route verified for both InMemoryGraph and NetworkXGraph!")


if __name__ == "__main__":
    test_mcp_exporter()
    test_graph_exporter()
    print("\n🎉 ALL EXPORT TESTS PASSED!")

