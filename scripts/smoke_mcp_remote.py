#!/usr/bin/env python3
"""Smoke a deployed CausaGanha MCP endpoint as a fresh HTTP client.

This is intentionally read-only. It verifies the cheap health boundary, the
real MCP catalog, one process lookup, and one archive search without relying
on a local stdio server or checkout-specific paths.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any
from urllib.parse import urljoin

import httpx
from fastmcp import Client


_REQUIRED_TOOLS = {"processo_consultar", "publicacoes_buscar"}


class RemoteSmokeError(RuntimeError):
    """Base failure for remote rollout proof."""


class InvalidRemoteToolError(RemoteSmokeError):
    """Raised when tools/list contains an invalid entry."""

    def __init__(self) -> None:
        super().__init__("tools/list retornou uma tool sem nome válido")


class UnhealthyRemoteError(RemoteSmokeError):
    """Raised when the cheap health boundary is not healthy."""

    def __init__(self, health: object) -> None:
        super().__init__(f"/health não está ok: {health!r}")


class RemoteCommitMismatchError(RemoteSmokeError):
    """Raised when the live service is not the revision being proved."""

    def __init__(self, expected: str, observed: object) -> None:
        super().__init__(
            "commit remoto diverge do deploy esperado: "
            f"esperado={expected!r}, observado={observed!r}"
        )


class MissingRemoteToolsError(RemoteSmokeError):
    """Raised when the live catalog lacks a required read-only tool."""

    def __init__(self, missing: list[str]) -> None:
        super().__init__(f"tools obrigatórias ausentes no endpoint remoto: {missing}")


def _mcp_url(service_url: str) -> str:
    return service_url.rstrip("/") + "/mcp"


def _health_url(service_url: str) -> str:
    return urljoin(service_url.rstrip("/") + "/", "health")


def _tool_name(tool: Any) -> str:
    name = getattr(tool, "name", None)
    if not isinstance(name, str) or not name:
        raise InvalidRemoteToolError
    return name


async def smoke(
    service_url: str,
    *,
    cnj: str,
    search_text: str,
    expected_commit: str | None = None,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as http:
        response = await http.get(_health_url(service_url))
        response.raise_for_status()
        health = response.json()

    if health.get("status") != "ok":
        raise UnhealthyRemoteError(health)
    if expected_commit and health.get("commit") != expected_commit:
        raise RemoteCommitMismatchError(expected_commit, health.get("commit"))

    async with Client(_mcp_url(service_url)) as client:
        tools = await client.list_tools()
        tool_names = {_tool_name(tool) for tool in tools}
        missing = sorted(_REQUIRED_TOOLS - tool_names)
        if missing:
            raise MissingRemoteToolsError(missing)

        await client.call_tool("processo_consultar", {"cnj": cnj})
        await client.call_tool(
            "publicacoes_buscar",
            {"texto": search_text, "limite": 1, "incluir_trecho": False},
        )

    return {
        "service_url": service_url.rstrip("/"),
        "mcp_url": _mcp_url(service_url),
        "health": health,
        "tool_count": len(tool_names),
        "required_tools": sorted(_REQUIRED_TOOLS),
        "smoke_calls": ["processo_consultar", "publicacoes_buscar"],
        "cnj": cnj,
        "search_text": search_text,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service-url", required=True)
    parser.add_argument("--cnj", required=True)
    parser.add_argument("--search-text", default="sentença")
    parser.add_argument("--expected-commit")
    args = parser.parse_args()

    evidence = asyncio.run(
        smoke(
            args.service_url,
            cnj=args.cnj,
            search_text=args.search_text,
            expected_commit=args.expected_commit,
        )
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
