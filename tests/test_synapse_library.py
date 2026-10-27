"""Comprehensive test suite for the Synapse library public APIs."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 1. Test clean, organized modular imports (lowercase synapse only)
import pytest
from synapse import BaseApp, SynapseApp, __version__
from synapse.models import Gemini, ollama, openAI
from synapse.connectors import (
    GmailConnectors,
    GooglePhotosConnectors,
    NotionConnectors,
    makeconnectors,
)
from synapse.oauth import GoogleOAuthService
from synapse.skills import Skill, makeskills
from synapse.resource import Resource


def test_library_imports():
    print(f"[1] Testing Synapse version: {__version__}")
    assert BaseApp is not None
    assert SynapseApp is BaseApp
    assert ollama is not None
    assert openAI is not None
    assert Gemini is not None
    assert GmailConnectors is not None
    assert GooglePhotosConnectors is not None
    assert NotionConnectors is not None
    assert GoogleOAuthService is not None
    assert callable(makeconnectors)
    assert makeskills is not None
    assert callable(makeskills)
    assert Resource is not None
    assert Skill is not None

    # Verify namespace isolation: top-level synapse only exports BaseApp / SynapseApp
    import synapse
    assert hasattr(synapse, "BaseApp")
    assert not hasattr(synapse, "makeconnectors")
    assert not hasattr(synapse, "make_connector")
    assert not hasattr(synapse, "makeskills")
    assert not hasattr(synapse, "make_skill")

    # Verify uppercase 'Synapse' is NOT registered
    import importlib
    import sys
    assert "Synapse" not in sys.modules
    with pytest.raises((ImportError, KeyError)):
        importlib.import_module("Synapse.models")

    print("    ✓ All modular imports and isolation verified!")


def test_models_instantiation():
    print("[2] Testing model providers instantiation...")
    local_m = ollama(model="qwen2.5:0.5b", base_url="http://localhost:11434")
    openai_m = openAI(api_key="test-key", model="gpt-4o-mini")
    gemini_m = Gemini(api_key="test-key", model="gemini-1.5-flash")

    assert local_m.model_name == "qwen2.5:0.5b"
    assert openai_m.model_name == "gpt-4o-mini"
    assert gemini_m.model_name == "gemini-1.5-flash"
    print("    ✓ Ollama, OpenAI, and Gemini models initialized cleanly!")


def test_connectors_and_oauth():
    print("[3] Testing connectors and OAuth service...")
    oauth_svc = GoogleOAuthService(
        credentials_path="test_credentials.json",
        token_path="test_token.json",
    )
    assert not oauth_svc.has_credentials()

    gmail = GmailConnectors(oauth_service=oauth_svc)
    assert gmail.name == "gmail"
    assert gmail.matches_intent("Check my unread emails")
    assert not gmail.matches_intent("What is the capital of France?")

    notion = NotionConnectors(api_key="secret_test")
    assert notion.name == "notion"
    assert notion.matches_intent("Search my notion notes")

    photos = GooglePhotosConnectors(oauth_service=oauth_svc)
    assert photos.name == "photos"
    assert photos.matches_intent("Show me photos from last month")

    # Test makeconnectors factory
    def mock_fetch(query: str = ""):
        return [{"id": "1", "title": f"Result for {query}"}]

    custom_conn = makeconnectors(
        name="custom_api",
        description="Custom documentation API",
        tools={"fetch": mock_fetch},
    )
    assert custom_conn.name == "custom_api"
    print("    ✓ Connectors, OAuth, and makeconnectors factory verified!")


def test_base_app_wiring():
    print("[4] Testing BaseApp initialization and FastAPI mounting...")
    app = BaseApp(
        title="Custom Intelligence App",
        model=ollama(model="qwen2.5:0.5b"),
        connectors=[
            GmailConnectors(),
            NotionConnectors(),
        ],
    )

    assert len(app.list_connectors()) == 2
    assert app.get_connector("gmail") is not None
    assert app.get_connector("notion") is not None

    fastapi_app = app.fastapi_app
    route_paths = [r.path for r in fastapi_app.routes if hasattr(r, "path")]
    assert "/chat" in route_paths
    assert "/sync/status" in route_paths
    assert "/inspector" in route_paths
    assert "/health" in route_paths
    assert "/graph/data" in route_paths
    print("    ✓ BaseApp wired with FastAPI routes & inspector dashboard!")


if __name__ == "__main__":
    test_library_imports()
    test_models_instantiation()
    test_connectors_and_oauth()
    test_base_app_wiring()
    print("\n🎉 ALL SYNAPSE LIBRARY TESTS PASSED!")
