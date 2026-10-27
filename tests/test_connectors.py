# tests/test_connectors.py
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from synapse.connectors import makeconnectors, GmailConnectors, GooglePhotosConnectors, NotionConnectors
from synapse.oauth import GoogleOAuthService


def test_custom_connector():
    def add_numbers(a: int, b: int) -> int:
        """Adds two integers together."""
        return a + b

    def greet(name: str = "World") -> str:
        """Returns a greeting string."""
        return f"Hello, {name}!"

    conn = makeconnectors(name="math_service", tools=[add_numbers, greet])
    assert conn.name == "math_service"
    assert len(conn.tools) == 2
    assert "add_numbers" in conn.tools
    assert "greet" in conn.tools


def test_builtin_connectors_instantiation():
    oauth = GoogleOAuthService(
        credentials_path="test_credentials.json",
        token_path="test_token.json",
    )
    gmail = GmailConnectors(oauth_service=oauth)
    photos = GooglePhotosConnectors(oauth_service=oauth)
    notion = NotionConnectors(api_key="test_notion_key")

    assert gmail.name == "gmail"
    assert photos.name == "photos"
    assert notion.name == "notion"


if __name__ == "__main__":
    test_custom_connector()
    test_builtin_connectors_instantiation()
    print("✓ All connector tests passed!")
