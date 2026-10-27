"""Tests for synapse.skills and synapse.resource modules."""

from __future__ import annotations

import tempfile
from pathlib import Path

# 1. Clean organized imports from submodules
from synapse import BaseApp
from synapse.models import OllamaModel
from synapse.resource import Resource
from synapse.skills import makeskills
from langchain_core.documents import Document


def test_skills_creation_and_parsing():
    print("[1] Testing Skill creation from inline string...")
    skill1 = makeskills(
        prompt="Always review Python code for type safety and PEP 8 conformity.",
        name="Python Reviewer",
        description="Enforces Python typing and clean architecture",
        tags=["python", "typing"],
    )
    assert skill1.name == "Python Reviewer"
    assert "type safety" in skill1.instructions
    assert "Python Reviewer" in skill1.format_prompt()
    assert "python" in skill1.tags

    print("    ✓ Inline skill creation verified!")

    print("[2] Testing Skill creation from Markdown with YAML frontmatter...")
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(
            """---
name: Database Expert
description: SQL query and indexing specialist
tags: [sql, postgres, performance]
---
# Database Guidelines
1. Always analyze query execution plans with EXPLAIN ANALYZE.
2. Use composite indexes for filtered and sorted columns.
"""
        )
        temp_skill_file = Path(f.name)

    try:
        skill2 = makeskills(temp_skill_file)
        assert skill2.name == "Database Expert"
        assert skill2.description == "SQL query and indexing specialist"
        assert "postgres" in skill2.tags
        assert "EXPLAIN ANALYZE" in skill2.instructions
        assert "Database Expert" in skill2.format_prompt()
        print("    ✓ Markdown file with YAML frontmatter parsed successfully!")
    finally:
        temp_skill_file.unlink(missing_ok=True)


def test_resource_ingestion_and_chaining():
    print("[3] Testing Resource ingestion and method chaining...")
    res = Resource("knowledge_base")

    # Add raw string with title
    res.add("Synapse uses FastEmbed ONNX for zero-Torch vector embeddings.", title="Embeddings Note")

    # Add temporary file
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write("# Architecture Overview\nSynapse combines Hybrid RAG with Multi-MCP connectors.")
        temp_doc_file = Path(f.name)

    try:
        # Add file and LangChain Document
        res.add(temp_doc_file)
        res.add(Document(page_content="Custom document object", metadata={"source": "custom_doc"}))

        # Test chaining
        res.add("Additional chained text content", source="chained")

        assert len(res) == 4
        assert res.name == "knowledge_base"

        chunks = res.get_chunks()
        assert len(chunks) >= 4
        print(f"    ✓ Resource ingested {len(res)} documents into {len(chunks)} indexable chunks!")
    finally:
        temp_doc_file.unlink(missing_ok=True)


def test_base_app_skills_and_resource_wiring():
    print("[4] Testing BaseApp integration with skills and resource...")
    # Create skills
    analyst_skill = makeskills(
        prompt="Provide concise executive summaries with bullet points.",
        name="Executive Analyst",
    )

    # Create resource
    docs_resource = Resource("engineering_docs")
    docs_resource.add("Metal acceleration is enabled by default on Apple Silicon macOS.")
    docs_resource.add("Ollama runs models locally with 4-bit and 8-bit quantization.")

    # Initialize BaseApp with skills, resource, and persistent storage enabled
    app = BaseApp(
        title="Intelligence Engine",
        model=OllamaModel(),
        skills=[analyst_skill],
        resource=docs_resource,
        persistent_storage=True,
    )

    # Verify skills and resources are registered
    assert len(app.list_skills()) == 1
    assert app.get_skill("Executive Analyst") is not None

    assert len(app.list_resources()) == 1
    assert app.get_resource("engineering_docs") is not None

    # Verify vector store received resource chunks
    assert app.vector_store.count() >= 2

    # Test adding a skill and resource dynamically
    coder_skill = app.add_skill("# Clean Coder\nWrite modular functions under 30 lines.")
    assert len(app.list_skills()) == 2
    assert coder_skill.name == "Clean Coder"

    app.add_resource("Extra dynamic resource note")
    assert len(app.list_resources()) == 2
    print("    ✓ Dynamic app.add_skill() and app.add_resource() verified!")

    # Verify FastAPI endpoints for skills and resources
    from fastapi.testclient import TestClient
    client = TestClient(app.fastapi_app)

    skills_res = client.get("/skills")
    assert skills_res.status_code == 200
    skills_json = skills_res.json()
    assert len(skills_json["skills"]) == 2
    assert skills_json["skills"][0]["name"] == "Executive Analyst"

    resources_res = client.get("/resources")
    assert resources_res.status_code == 200
    resources_json = resources_res.json()
    assert len(resources_json["resources"]) == 2

    health_res = client.get("/health")
    assert health_res.status_code == 200
    health_json = health_res.json()
    assert "Executive Analyst" in health_json["skills"]
    assert "engineering_docs" in health_json["resources"]
    print("    ✓ FastAPI /skills, /resources, and enriched /health endpoints verified!")


def test_premade_skills_and_templates():
    from synapse.skills import SkillRegistry, SkillTemplate, list_premade_skills, load_premade_skill

    # 1. Test listing premade skills
    names = list_premade_skills()
    assert "rag-analyst" in names
    assert "knowledge-graph" in names
    assert "mcp-orchestrator" in names
    assert "mlflow-evaluator" in names
    assert "template" in names

    # 2. Test loading premade skills
    for name in names:
        sk = load_premade_skill(name)
        assert sk.name
        assert sk.instructions
        assert sk.format_prompt()

    # 3. Test SkillTemplate
    tmpl = SkillTemplate.get_template(
        name="api-tester",
        description="Tests REST and GraphQL APIs",
        tags=["api", "testing"],
    )
    assert "name: api-tester" in tmpl
    assert "description: Tests REST and GraphQL APIs" in tmpl

    created_skill = SkillTemplate.create(
        name="api-tester",
        description="Tests REST endpoints",
        instructions="Always check HTTP 200 responses.",
    )
    assert created_skill.name == "api-tester"
    assert "HTTP 200" in created_skill.instructions

    # 4. Test SkillRegistry
    registry = SkillRegistry()
    registry.register(created_skill)
    assert len(registry) == 1
    assert registry.get("api-tester") is not None
    assert registry.get("api-tester").name == "api-tester"


if __name__ == "__main__":
    test_skills_creation_and_parsing()
    test_resource_ingestion_and_chaining()
    test_base_app_skills_and_resource_wiring()
    test_premade_skills_and_templates()
    print("\n🎉 ALL SYNAPSE SKILLS & RESOURCE TESTS PASSED!")
