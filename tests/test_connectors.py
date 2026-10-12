# tests/test_connectors.py
import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.mcp_client import mcp_manager


async def test_gmail_connector():
    print("[1] Discovering tools on Gmail MCP server...")
    try:
        tools = await mcp_manager.list_tools("gmail")
        print("Available Tools:")
        for t in tools:
            print(f" - {t['name']}: {t.get('description', 'No description')}")
    except Exception as e:
        print(f"Failed to list tools: {e}")
        return

    print("\n[2] Calling 'search_emails' via MCP client (stdio)...")
    try:
        # Note: If OAuth token is not configured yet, this will exercise the call path
        emails = await mcp_manager.call_tool(
            server_name="gmail",
            tool_name="search_emails",
            arguments={"query": "label:INBOX", "max_results": 2}
        )
        print(f"Result count: {len(emails) if isinstance(emails, list) else 1}")
        print("Sample output:", emails)
    except Exception as e:
        print(f"Execution notice: {e}")


if __name__ == "__main__":
    asyncio.run(test_gmail_connector())