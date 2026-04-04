"""Tribunal list management — hardcoded fallback + live API merge."""

from __future__ import annotations

import httpx
import structlog

from causaganha.config import TRIBUNAIS
from djen_backup.retry import request_with_retry


log = structlog.get_logger()


async def fetch_tribunal_list_from_api(
    client: httpx.AsyncClient,
    base_url: str,
) -> list[str]:
    """Fetch tribunal codes from the DJEN proxy API."""
    url = f"{base_url}/api/v1/comunicacao/tribunal"
    try:
        resp = await request_with_retry(client, "GET", url)
        resp.raise_for_status()
        raw = resp.json()
        if not isinstance(raw, list):
            log.warning("tribunal_api_unexpected_payload", type=type(raw).__name__)
            return []
        data: list[object] = raw
        codes: list[str] = []
        for group in data:
            if not isinstance(group, dict):
                continue
            instituicoes = group.get("instituicoes", [])
            if isinstance(instituicoes, list):
                for inst in instituicoes:
                    if isinstance(inst, dict):
                        sigla = inst.get("sigla")
                        if isinstance(sigla, str) and sigla:
                            codes.append(sigla)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("tribunal_api_fetch_failed", error=str(exc))
        return []
    return codes


async def get_tribunal_list(
    client: httpx.AsyncClient,
    base_url: str,
) -> list[str]:
    """Return merged (union) tribunal list: hardcoded + API."""
    api_codes = await fetch_tribunal_list_from_api(client, base_url)
    merged = sorted(set(TRIBUNAIS) | set(api_codes))
    log.info(
        "tribunal_list_loaded",
        hardcoded=len(TRIBUNAIS),
        from_api=len(api_codes),
        merged=len(merged),
    )
    return merged
