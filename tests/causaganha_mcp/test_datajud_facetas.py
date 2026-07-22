"""Behavior tests for the ``datajud_facetas`` MCP tool (RFC 0013 Fase 3B).

Unlike Fase 3A's status tools, `facetas` hits a real HTTP endpoint (the
public DataJud API) — so these tests mock it with `respx` (the same pattern
`tests/datajud/test_datajud_enrich.py` uses for the CLI) instead of building
a local manifest fixture. The behavior under test is the mapping from
`datajud.client`'s error taxonomy to `fastmcp.exceptions.ToolError` — a
crash here would corrupt the JSON-RPC transport (see
`test_stdio_transport.py`), so every DataJud failure mode must surface as a
structured tool error instead.
"""

from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp.exceptions import ToolError

from causaganha_mcp.server import build_server
from datajud.client import search_endpoint


ENDPOINT = search_endpoint("tjro")


def _facetas_payload(total: int, buckets: list[tuple[str, int]]) -> dict:
    return {
        "hits": {"total": {"value": total, "relation": "eq"}},
        "aggregations": {
            "facetas": {"buckets": [{"key": chave, "doc_count": qtd} for chave, qtd in buckets]}
        },
    }


@pytest.fixture
def mcp():
    return build_server()


async def _facetas_fn(mcp):
    tool = await mcp.get_tool("datajud_facetas")
    return tool.fn


async def test_facetas_success_returns_total_and_buckets(mcp) -> None:
    fn = await _facetas_fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(
            200, json=_facetas_payload(42, [("Procedimento Comum Cível", 30), ("Execução", 12)])
        )
        result = await fn(tribunal="tjro", por="classe", limite=15)

    assert result.tribunal == "tjro"
    assert result.por == "classe"
    assert result.total == 42
    assert [(b.chave, b.qtd) for b in result.buckets] == [
        ("Procedimento Comum Cível", 30),
        ("Execução", 12),
    ]


async def test_facetas_auth_error_becomes_tool_error(mcp) -> None:
    fn = await _facetas_fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(401)
        with pytest.raises(ToolError, match="401"):
            await fn(tribunal="tjro", por="classe", limite=15)


async def test_facetas_rate_limit_exhaustion_becomes_tool_error(mcp, monkeypatch) -> None:
    from datajud import service

    original = service.DataJudClient
    monkeypatch.setattr(
        service,
        "DataJudClient",
        lambda **kw: original(**{**kw, "backoff_base": 0.0, "max_retries": 1}),
    )

    fn = await _facetas_fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(429)
        with pytest.raises(ToolError, match="rate-limited"):
            await fn(tribunal="tjro", por="classe", limite=15)


async def test_facetas_es_rejection_exhaustion_becomes_tool_error(mcp, monkeypatch) -> None:
    from datajud import service

    original = service.DataJudClient
    monkeypatch.setattr(
        service,
        "DataJudClient",
        lambda **kw: original(**{**kw, "backoff_base": 0.0, "max_retries": 1}),
    )

    fn = await _facetas_fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(
            200,
            json={"error": {"root_cause": [{"type": "es_rejected_execution_exception"}]}},
        )
        with pytest.raises(ToolError, match="rate-limited"):
            await fn(tribunal="tjro", por="classe", limite=15)


async def test_facetas_generic_es_error_becomes_tool_error(mcp) -> None:
    fn = await _facetas_fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(
            200,
            json={"error": {"root_cause": [{"type": "query_shard_exception"}]}},
        )
        with pytest.raises(ToolError, match="DataJud query failed"):
            await fn(tribunal="tjro", por="classe", limite=15)


async def test_facetas_other_http_status_becomes_tool_error(mcp) -> None:
    fn = await _facetas_fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(500)
        with pytest.raises(ToolError, match="500"):
            await fn(tribunal="tjro", por="classe", limite=15)


async def test_facetas_network_error_becomes_tool_error(mcp, monkeypatch) -> None:
    from datajud import service

    original = service.DataJudClient
    monkeypatch.setattr(
        service,
        "DataJudClient",
        lambda **kw: original(**{**kw, "backoff_base": 0.0, "max_retries": 1}),
    )

    fn = await _facetas_fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).mock(side_effect=httpx.ConnectError("boom"))
        with pytest.raises(ToolError, match="Network error"):
            await fn(tribunal="tjro", por="classe", limite=15)


async def test_facetas_non_json_response_becomes_tool_error(mcp) -> None:
    """A WAF/gateway can return HTML under HTTP 200 — must not leak a bare ValueError."""
    fn = await _facetas_fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(
            200, content=b"<html>blocked by WAF</html>", headers={"content-type": "text/html"}
        )
        with pytest.raises(ToolError, match="unparseable"):
            await fn(tribunal="tjro", por="classe", limite=15)


async def test_facetas_uses_a_tighter_budget_than_the_ingestion_client(mcp, monkeypatch) -> None:
    """Production must not inherit `DataJudClient`'s ~10-minute ingestion worst case.

    Spies on the kwargs the tool actually passes to `DataJudClient` — no
    real retry/backoff needs to happen (the mocked response succeeds on the
    first attempt), so this is a fast, direct check that the tool's call
    path uses its own internal budget rather than the client's defaults.
    """
    from causaganha_mcp.tools import datajud as tool_module
    from datajud import service

    captured: dict = {}
    original = service.DataJudClient

    def spy(**kwargs: float | str) -> object:
        captured.update(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(service, "DataJudClient", spy)

    fn = await _facetas_fn(mcp)
    with respx.mock() as router:
        router.post(ENDPOINT).respond(200, json=_facetas_payload(1, [("x", 1)]))
        await fn(tribunal="tjro", por="classe", limite=15)

    assert captured["timeout"] == tool_module._FACETAS_TIMEOUT
    assert captured["max_retries"] == tool_module._FACETAS_MAX_RETRIES
    assert captured["backoff_base"] == tool_module._FACETAS_BACKOFF_BASE
