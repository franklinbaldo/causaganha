"""DJEN 403 handling — CloudFront blocks must surface as DJENRateLimitedError."""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from djen_backup.djen import DJENNotFoundError, DJENRateLimitedError, get_caderno_url


@pytest.mark.asyncio
async def test_get_caderno_url_raises_rate_limited_on_403() -> None:
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith="https://djen.example/").respond(403)
        async with httpx.AsyncClient() as client:
            with pytest.raises(DJENRateLimitedError):
                await get_caderno_url(client, "https://djen.example", "TJSP", date(2024, 1, 2))


@pytest.mark.asyncio
async def test_get_caderno_url_raises_not_found_on_404() -> None:
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith="https://djen.example/").respond(404)
        async with httpx.AsyncClient() as client:
            with pytest.raises(DJENNotFoundError) as exc_info:
                await get_caderno_url(client, "https://djen.example", "TJSP", date(2024, 1, 2))
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_caderno_url_raises_not_found_on_400_holiday() -> None:
    with respx.mock(assert_all_called=False) as router:
        router.get(url__startswith="https://djen.example/").respond(400)
        async with httpx.AsyncClient() as client:
            with pytest.raises(DJENNotFoundError) as exc_info:
                await get_caderno_url(client, "https://djen.example", "TJSP", date(2024, 1, 2))
    assert exc_info.value.status_code == 400
