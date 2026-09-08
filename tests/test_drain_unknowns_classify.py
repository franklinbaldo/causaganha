"""Unit tests for ``scripts.drain_unknowns._classify``.

Mirrors ``tests/djen_backup/test_classify_djen.py``'s coverage of the sibling
``_classify_djen_status`` in ``djen_backup.engine``. Both functions map a DJEN
call outcome to a raw_status string that ``interpret_djen_raw()`` later
derives ``djen_status`` from — per CLAUDE.md, a bare "200" for HTTP 200 with
body ``{"status": "Sem comunicações"}`` (no download URL) is genuinely absent,
not available, and recording it as "200" reproduces the historical ~79K-row
false-"available" bug.
"""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from djen_backup.djen import DJENNotFoundError, DJENRateLimitedError
from djen_backup.manifest import interpret_djen_raw
from scripts import drain_unknowns


@pytest.mark.asyncio
async def test_classify_returns_no_publications_for_200_sem_comunicacoes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # "Sem comunicações" = HTTP 200, empty body, no URL. get_caderno_url raises
    # DJENNotFoundError(status_code=200). This is genuinely absent — it must
    # NOT be recorded as "200" (which interpret_djen_raw maps to "available").
    async def _empty(*_args: object, **_kwargs: object) -> str:
        raise DJENNotFoundError(status_code=200, reason="No publications")

    monkeypatch.setattr(drain_unknowns, "get_caderno_url", _empty)

    raw = await drain_unknowns._classify(
        client=object(),  # type: ignore[arg-type]
        base="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
    )

    assert raw == "no_publications"
    # And the derived status must be absent, never available.
    assert interpret_djen_raw(raw) == "absent"


@pytest.mark.asyncio
async def test_classify_returns_status_code_on_genuine_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _missing(*_args: object, **_kwargs: object) -> str:
        raise DJENNotFoundError(status_code=404, reason="Not found")

    monkeypatch.setattr(drain_unknowns, "get_caderno_url", _missing)

    raw = await drain_unknowns._classify(
        client=object(),  # type: ignore[arg-type]
        base="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
    )

    assert raw == "404"
    assert interpret_djen_raw(raw) == "absent"


@pytest.mark.asyncio
async def test_classify_returns_200_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ok(*_args: object, **_kwargs: object) -> str:
        return "https://example/zip"

    monkeypatch.setattr(drain_unknowns, "get_caderno_url", _ok)

    raw = await drain_unknowns._classify(
        client=object(),  # type: ignore[arg-type]
        base="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
    )

    assert raw == "200"
    assert interpret_djen_raw(raw) == "available"


@pytest.mark.asyncio
async def test_classify_returns_403_on_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _blocked(*_args: object, **_kwargs: object) -> str:
        raise DJENRateLimitedError("blocked")

    monkeypatch.setattr(drain_unknowns, "get_caderno_url", _blocked)

    raw = await drain_unknowns._classify(
        client=object(),  # type: ignore[arg-type]
        base="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
    )

    assert raw == "403"


@pytest.mark.asyncio
async def test_classify_returns_timeout_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _timeout(*_args: object, **_kwargs: object) -> str:
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr(drain_unknowns, "get_caderno_url", _timeout)

    raw = await drain_unknowns._classify(
        client=object(),  # type: ignore[arg-type]
        base="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
    )

    assert raw == "timeout"


@pytest.mark.asyncio
async def test_classify_returns_network_on_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _network(*_args: object, **_kwargs: object) -> str:
        raise httpx.ConnectError("reset")

    monkeypatch.setattr(drain_unknowns, "get_caderno_url", _network)

    raw = await drain_unknowns._classify(
        client=object(),  # type: ignore[arg-type]
        base="https://djen.example",
        tribunal="TJSP",
        d=date(2024, 1, 2),
    )

    assert raw == "network"
