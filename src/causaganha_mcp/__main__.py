"""Entry point for ``causaganha-mcp`` — runs the server over stdio."""

from __future__ import annotations

import sys

import structlog

from causaganha_mcp.server import mcp


def _configure_stdio_safe_logging() -> None:
    """Send structlog output to stderr, never stdout.

    In MCP stdio transport, stdout is exclusively the JSON-RPC channel — a
    single ordinary log line (e.g. ``ManifestSTJ.load()``'s
    ``log.info("stj_manifest_loaded", ...)``, or
    ``SyncManifest.load_from_disk()``'s equivalent) written to stdout via
    structlog's default ``PrintLogger`` corrupts every message after it.
    Called from ``main()``, not at import time — importing this module (a
    test, another tool) must not reconfigure global structlog state; only
    actually running the server should.
    """
    structlog.configure(logger_factory=structlog.PrintLoggerFactory(file=sys.stderr))


def main() -> None:
    """Run the MCP server over stdio (local, single-client transport)."""
    _configure_stdio_safe_logging()
    mcp.run()


if __name__ == "__main__":
    main()
