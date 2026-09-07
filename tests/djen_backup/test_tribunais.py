from __future__ import annotations

import httpx
import pytest

from causaganha.config import TRIBUNAIS
from djen_backup.tribunais import fetch_tribunal_list_from_api, get_tribunal_list


_BASE_URL = "https://djen-proxy.example"
_TRIBUNAL_ENDPOINT = f"{_BASE_URL}/api/v1/comunicacao/tribunal"


def _payload(*siglas: str) -> list[dict[str, object]]:
    return [{"instituicoes": [{"sigla": sigla} for sigla in siglas]}]


@pytest.mark.asyncio
async def test_get_tribunal_list_merges_new_api_codes_into_the_hardcoded_baseline(
    mock_api,
) -> None:
    """A live API response must add to the hardcoded list, never replace it."""
    mock_api.get(_TRIBUNAL_ENDPOINT).respond(200, json=_payload("TJXX"))

    async with httpx.AsyncClient() as client:
        result = await get_tribunal_list(client, _BASE_URL)

    assert "TJXX" in result
    assert "TJRO" in result, (
        "a partial/incomplete API response must not drop hardcoded tribunals that the API omitted"
    )


@pytest.mark.asyncio
async def test_get_tribunal_list_never_returns_fewer_than_the_hardcoded_baseline(
    mock_api,
) -> None:
    mock_api.get(_TRIBUNAL_ENDPOINT).respond(200, json=_payload("TJXX"))

    async with httpx.AsyncClient() as client:
        result = await get_tribunal_list(client, _BASE_URL)

    assert set(TRIBUNAIS) <= set(result)


@pytest.mark.asyncio
async def test_get_tribunal_list_falls_back_to_hardcoded_when_api_returns_nothing(
    mock_api,
) -> None:
    mock_api.get(_TRIBUNAL_ENDPOINT).respond(200, json=[])

    async with httpx.AsyncClient() as client:
        result = await get_tribunal_list(client, _BASE_URL)

    assert result == sorted(TRIBUNAIS)


@pytest.mark.asyncio
async def test_get_tribunal_list_falls_back_to_hardcoded_when_api_request_fails(
    mock_api,
) -> None:
    mock_api.get(_TRIBUNAL_ENDPOINT).respond(500)

    async with httpx.AsyncClient() as client:
        result = await get_tribunal_list(client, _BASE_URL)

    assert result == sorted(TRIBUNAIS)


@pytest.mark.asyncio
async def test_fetch_tribunal_list_from_api_extracts_siglas_from_nested_groups(
    mock_api,
) -> None:
    mock_api.get(_TRIBUNAL_ENDPOINT).respond(200, json=_payload("TJXX", "TJYY"))

    async with httpx.AsyncClient() as client:
        codes = await fetch_tribunal_list_from_api(client, _BASE_URL)

    assert codes == ["TJXX", "TJYY"]
