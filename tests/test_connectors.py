# tests/test_connectors.py
import asyncio
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
    assert conn.default_tool == "add_numbers"


def test_single_callable_and_param_pruning():
    """Verifies single function tool acceptance, argument pruning, and schema caching."""
    def multiply(x: int, y: int) -> int:
        """Multiplies x and y."""
        return x * y

    # 1. Single function passed directly to tools
    conn = makeconnectors(name="calc", tools=multiply)
    assert len(conn.tools) == 1
    assert "multiply" in conn.tools
    assert conn.default_tool == "multiply"

    async def _run():
        # 2. Schema caching verification
        tools_1 = await conn.list_tools()
        tools_2 = await conn.list_tools()
        assert tools_1 is tools_2  # Same cached list reference

        # 3. Parameter pruning: calling with hallucinated arguments must NOT crash
        res = await conn.call_tool("multiply", {"x": 6, "y": 7, "hallucinated_param": "ignore_me"})
        assert res == 42

    asyncio.run(_run())


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
