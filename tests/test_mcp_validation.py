"""Tests for MCP server validation, stdio handshake, tools, prompts, and resources."""

from __future__ import annotations

from synapse import BaseApp
from synapse.connectors import makeconnectors
from synapse.export.mcp_exporter import MCPExporter
from synapse.resource import Resource
from synapse.skills import load_premade_skill


def test_mcp_server_full_capabilities():
    """Verifies that create_mcp_server wires tools, prompts, and resources cleanly."""
    # 1. Create a dummy connector
    def mock_search(query: str = "", max_results: int = 5) -> str:
        """Search mock documents."""
        return f"Results for: {query}"

    conn = makeconnectors(name="test_tool", tools={"search": mock_search})

    # 2. Create resource
    res = Resource("test_docs")
    res.add("Synapse is a modular AI framework.", title="Framework Intro")

    # 3. Create app
    app = BaseApp(
        title="MCP Test App",
        connectors=[conn],
        resource=res,
        skills=[load_premade_skill("rag-analyst")],
        persistent_storage=False,
        Visualize_graph=False,
    )

    server = MCPExporter.create_mcp_server(app)

    # 4. Assert tools are registered and parameter schema is clean (no required kwargs!)
    assert hasattr(server, "_tool_manager")
    tools = server._tool_manager._tools
    assert "test_tool_search" in tools or "search" in tools

    for t_name, tool in tools.items():
        params = tool.parameters
        # Critical bug check: kwargs must NOT be in required list!
        required = params.get("required", [])
        assert "kwargs" not in required, f"Tool '{t_name}' has broken 'kwargs' in required list!"

    # 5. Assert prompts are registered (fixing 'Includes Prompts' checklist)
    assert hasattr(server, "_prompt_manager")
    prompts = server._prompt_manager._prompts
    assert len(prompts) >= 4  # Core prompts + rag_analyst
    assert "rag_synthesis" in prompts
    assert "code_review" in prompts
    assert "rag_analyst" in prompts

    # 6. Assert resources are registered (fixing 'Includes Resources' checklist)
    assert hasattr(server, "_resource_manager")
    resources = server._resource_manager._resources
    assert len(resources) >= 3  # status, skills, test_docs
    assert "resource://synapse/status" in resources
    assert "resource://synapse/skills" in resources
    assert "resource://synapse/resources/test_docs" in resources


def test_standalone_connector_mcp_export():
    """Verifies that an individual connector can export to an MCP server directly."""
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    conn = makeconnectors(name="math_tools", tools={"add": add})
    server = conn.to_mcp_server()
    assert server is not None
    assert "add" in server._tool_manager._tools or "math_tools_add" in server._tool_manager._tools
