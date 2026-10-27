"""Command-line interface for running the Synapse AI inspector server and MCP stdio engine."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from synapse.app import BaseApp
from synapse.connectors.gmail import GmailConnector
from synapse.connectors.notion import NotionConnector
from synapse.export.mcp_exporter import MCPExporter
from synapse.models.ollama import OllamaModel


def build_default_app(data_dir: str = "data") -> BaseApp:
    """Constructs the default CLI Synapse application instance."""
    return BaseApp(
        title="Synapse AI",
        data_dir=Path(data_dir),
        model=OllamaModel(),
        connectors=[
            GmailConnector(),
            NotionConnector(),
        ],
        persistent_storage=True,
        Visualize_graph=True,
    )


def main() -> None:
    """CLI entrypoint: `synapse`, `synapse mcp`, `synapse serve`, or `python -m synapse.cli`."""
    parser = argparse.ArgumentParser(
        description="Synapse — Multi-MCP & Hybrid RAG Framework",
    )
    parser.add_argument(
        "subcommand",
        nargs="?",
        default=None,
        choices=["serve", "mcp", "export"],
        help="Action to run: 'serve' (web inspector/API), 'mcp' (stdio server for Claude/Cursor), or 'export' (generate config)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port number to listen on (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn hot-reloading",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Storage directory for ChromaDB and NetworkX graph (default: data)",
    )
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Shortcut to run in stdio MCP mode",
    )
    parser.add_argument(
        "--output",
        default="claude_desktop_config.json",
        help="Destination path for 'export' subcommand",
    )

    args = parser.parse_args()

    # Intelligent Auto-Detection:
    # If subcommand is not specified and stdin is a pipe (e.g. Claude Desktop, Cursor,
    # or MCP Registry Validator invoking `uvx synapse-framework`), default to 'mcp' stdio.
    # Otherwise, default to interactive 'serve'.
    subcmd = args.subcommand
    if subcmd is None:
        if args.mcp:
            subcmd = "mcp"
        elif not sys.stdin.isatty():
            subcmd = "mcp"
        else:
            subcmd = "serve"

    if subcmd == "mcp" or args.mcp:
        # Guarantee 100% clean stdout for JSON-RPC MCP frames
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        app = build_default_app(data_dir=args.data_dir)
        app.run_mcp(transport="stdio")
    elif subcmd == "export":
        app = build_default_app(data_dir=args.data_dir)
        cfg_path = MCPExporter.save_claude_desktop_config(app, filepath=args.output)
        print(f"✓ Claude Desktop config saved to: {cfg_path}")
    else:
        app = build_default_app(data_dir=args.data_dir)
        app.run(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
