"""Unit tests for ``_classify_djen_status`` — the DJEN-call → raw_status map.

Verifies the contract documented in CLAUDE.md:
- 200 → "200" (available)
- 404 / 400 → status code (genuine absent)
- 403 → "403" (transient WAF, no breaker hit)
- timeout → "timeout"
- network / unknown HTTP error → "network"
- HTTPStatusError → str(status_code)
"""

from __future__ import annotations

from datetime import date

import pytest
from aiolimiter import AsyncLimiter

from djen_backup import engine as engine_module
from djen_backup.djen import DJENNotFoundError, DJENRateLimitedError
from djen_backup.engine import _classify_djen_status


def _limiter() -> AsyncLimiter:
    # generous limiter so tests aren't gated on real-clock waits
    return AsyncLimiter(max_rate=100, time_period=1)


@pytest.mark.asyncio
async def test_classify_returns_200_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ok(*_args: object, **_kwargs: object) -> str:
        return "https://example/zip"

    monkeypatch.setattr(engine_module, "get_caderno_url", _ok)

    raw = await _classify_djen_status(
        client=object(),  # type: ignore[arg-type]
        proxy_url="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
        djen_limiter=_limiter(),
    )
    assert raw == "200"


@pytest.mark.asyncio
async def test_classify_returns_status_code_on_djen_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _missing(*_args: object, **_kwargs: object) -> str:
        raise DJENNotFoundError(status_code=404, reason="Not found")

    monkeypatch.setattr(engine_module, "get_caderno_url", _missing)

    raw = await _classify_djen_status(
        client=object(),  # type: ignore[arg-type]
        proxy_url="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
        djen_limiter=_limiter(),
    )
    assert raw == "404"


@pytest.mark.asyncio
async def test_classify_returns_400_for_holiday(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _holiday(*_args: object, **_kwargs: object) -> str:
        raise DJENNotFoundError(status_code=400, reason="Holiday")

    monkeypatch.setattr(engine_module, "get_caderno_url", _holiday)

    raw = await _classify_djen_status(
        client=object(),  # type: ignore[arg-type]
        proxy_url="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
        djen_limiter=_limiter(),
    )
    assert raw == "400"


@pytest.mark.asyncio
async def test_classify_returns_no_publications_for_200_sem_comunicacoes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # "Sem comunicações" = HTTP 200, empty body, no URL. get_caderno_url raises
    # DJENNotFoundError(status_code=200). This is genuinely absent — it must NOT
    # be recorded as "200" (which interpret_djen_raw maps to "available").
    async def _empty(*_args: object, **_kwargs: object) -> str:
        raise DJENNotFoundError(status_code=200, reason="No publications")

    monkeypatch.setattr(engine_module, "get_caderno_url", _empty)

    raw = await _classify_djen_status(
        client=object(),  # type: ignore[arg-type]
        proxy_url="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
        djen_limiter=_limiter(),
    )
    assert raw == "no_publications"
    # And the derived status must be absent, never available.
    from djen_backup.manifest import interpret_djen_raw

    assert interpret_djen_raw(raw) == "absent"
    assert interpret_djen_raw("200") == "available"


@pytest.mark.asyncio
async def test_classify_returns_403_for_cloudfront_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _waf(*_args: object, **_kwargs: object) -> str:
        raise DJENRateLimitedError("CloudFront block")  # noqa: EM101, TRY003

    monkeypatch.setattr(engine_module, "get_caderno_url", _waf)

    raw = await _classify_djen_status(
        client=object(),  # type: ignore[arg-type]
        proxy_url="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
        djen_limiter=_limiter(),
    )
    assert raw == "403"


@pytest.mark.asyncio
async def test_classify_returns_network_on_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    async def _boom(*_args: object, **_kwargs: object) -> str:
        raise httpx.HTTPError("Server error: 502")  # noqa: EM101, TRY003

    monkeypatch.setattr(engine_module, "get_caderno_url", _boom)

    raw = await _classify_djen_status(
        client=object(),  # type: ignore[arg-type]
        proxy_url="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
        djen_limiter=_limiter(),
    )
    assert raw == "network"


@pytest.mark.asyncio
async def test_classify_returns_timeout_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    async def _slow(*_args: object, **_kwargs: object) -> str:
        raise httpx.ReadTimeout("read timed out")  # noqa: EM101, TRY003

    monkeypatch.setattr(engine_module, "get_caderno_url", _slow)

    raw = await _classify_djen_status(
        client=object(),  # type: ignore[arg-type]
        proxy_url="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
        djen_limiter=_limiter(),
    )
    assert raw == "timeout"


@pytest.mark.asyncio
async def test_classify_returns_status_code_on_http_status_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import httpx

    async def _five_oh_two(*_args: object, **_kwargs: object) -> str:
        request = httpx.Request("GET", "https://djen.example")
        response = httpx.Response(502, request=request)
        raise httpx.HTTPStatusError("502", request=request, response=response)  # noqa: EM101

    monkeypatch.setattr(engine_module, "get_caderno_url", _five_oh_two)

    raw = await _classify_djen_status(
        client=object(),  # type: ignore[arg-type]
        proxy_url="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
        djen_limiter=_limiter(),
    )
    assert raw == "502"
