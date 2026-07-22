"""Entry point for ``causaganha-mcp`` — runs the server over stdio."""

from __future__ import annotations

from causaganha_mcp.server import mcp


def main() -> None:
    """Run the MCP server over stdio (local, single-client transport)."""
    mcp.run()


if __name__ == "__main__":
    main()
