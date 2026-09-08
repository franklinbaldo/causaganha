"""Unit tests for ``scripts.backfill_probe._probe_one``'s live classification.

``backfill_probe.py`` exists to spot drift between the manifest's recorded
``djen_raw`` and what the DJEN proxy returns live right now (its own module
docstring). Per CLAUDE.md, a bare HTTP 200 does NOT mean "available" — DJEN
returns 200 with body ``{"status": "Sem comunicações"}`` for a genuinely
absent caderno (no download URL). Every other DJEN caller in this codebase
(``djen_backup.engine._classify_djen_status``, ``djen_backup.probe._probe_one``,
``scripts.drain_unknowns``) derives its raw code from ``get_caderno_url``'s
result, which special-cases this. ``_probe_one`` used to classify
``live_raw`` from the bare HTTP status code instead, so a genuinely-absent
live probe was reported as ``"200"``/"available" -- exactly the historical
~79K-row bug the manifest itself was fixed to stop reproducing, this time in
the diagnostic tool meant to catch that class of drift.
"""

from __future__ import annotations

import asyncio
from datetime import date

import httpx
import pytest
import respx

from scripts.backfill_probe import _probe_one


@pytest.mark.asyncio
async def test_probe_one_reports_no_publications_for_200_sem_comunicacoes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DJEN_PROXY_URL", "https://djen.example")
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith="https://djen.example/").respond(
            200, json={"status": "Sem comunicações"}
        )
        async with httpx.AsyncClient() as client:
            sem = asyncio.Semaphore(1)
            out = await _probe_one(client, "TJSP", date(2024, 1, 2).isoformat(), sem)

    assert out["live_raw"] == "no_publications"


@pytest.mark.asyncio
async def test_probe_one_reports_200_when_a_download_url_is_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DJEN_PROXY_URL", "https://djen.example")
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith="https://djen.example/").respond(
            200, json={"url": "https://example.com/caderno.zip"}
        )
        async with httpx.AsyncClient() as client:
            sem = asyncio.Semaphore(1)
            out = await _probe_one(client, "TJSP", date(2024, 1, 2).isoformat(), sem)

    assert out["live_raw"] == "200"


@pytest.mark.asyncio
async def test_probe_one_reports_403_as_rate_limited_not_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DJEN_PROXY_URL", "https://djen.example")
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith="https://djen.example/").respond(403)
        async with httpx.AsyncClient() as client:
            sem = asyncio.Semaphore(1)
            out = await _probe_one(client, "TJSP", date(2024, 1, 2).isoformat(), sem)

    assert out["live_raw"] == "403"


@pytest.mark.asyncio
async def test_probe_one_reports_404_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DJEN_PROXY_URL", "https://djen.example")
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith="https://djen.example/").respond(404)
        async with httpx.AsyncClient() as client:
            sem = asyncio.Semaphore(1)
            out = await _probe_one(client, "TJSP", date(2024, 1, 2).isoformat(), sem)

    assert out["live_raw"] == "404"
