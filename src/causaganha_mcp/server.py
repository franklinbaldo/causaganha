"""FastMCP server assembly for ``causaganha_mcp`` (RFC 0013 Fase 3, RFC 0014).

Tool composition itself lives in ``causaganha_mcp.profiles`` (#1244), which
declares the public/product profile and the operator/local profile
explicitly. ``build_server()`` is the stdio entrypoint's server: the
operator profile, unchanged in catalog shape from before the split.
"""

from __future__ import annotations

from fastmcp import FastMCP

from causaganha_mcp.profiles import build_operator_server


def build_server() -> FastMCP:
    """Construct the full ``causaganha_mcp`` catalog used by the stdio entrypoint."""
    return build_operator_server()


mcp = build_server()
