"""Tribunal list management — hardcoded fallback + live API merge."""

from __future__ import annotations

import httpx
import structlog

from djen_backup.retry import request_with_retry

log = structlog.get_logger()

TRIBUNAIS: list[str] = [
    "CJF",
    "PJeCor",
    "SEEU",
    "TRF1",
    "TRF2",
    "TRF3",
    "TRF4",
    "TRF5",
    "TRF6",
    "STF",
    "STJ",
    "TST",
    "TSE",
    "STM",
    "CNJ",
    "TJAC",
    "TJAL",
    "TJAM",
    "TJAP",
    "TJBA",
    "TJCE",
    "TJDFT",
    "TJES",
    "TJGO",
    "TJMA",
    "TJMG",
    "TJMS",
    "TJMT",
    "TJPA",
    "TJPB",
    "TJPE",
    "TJPI",
    "TJPR",
    "TJRJ",
    "TJRN",
    "TJRO",
    "TJRR",
    "TJRS",
    "TJSC",
    "TJSE",
    "TJSP",
    "TJTO",
    "TJMMG",
    "TJMRS",
    "TJMSP",
    "TRT1",
    "TRT2",
    "TRT3",
    "TRT4",
    "TRT5",
    "TRT6",
    "TRT7",
    "TRT8",
    "TRT9",
    "TRT10",
    "TRT11",
    "TRT12",
    "TRT13",
    "TRT14",
    "TRT15",
    "TRT16",
    "TRT17",
    "TRT18",
    "TRT19",
    "TRT20",
    "TRT21",
    "TRT22",
    "TRT23",
    "TRT24",
    "TRE-AC",
    "TRE-AL",
    "TRE-AM",
    "TRE-AP",
    "TRE-BA",
    "TRE-CE",
    "TRE-DF",
    "TRE-ES",
    "TRE-GO",
    "TRE-MA",
    "TRE-MG",
    "TRE-MS",
    "TRE-MT",
    "TRE-PA",
    "TRE-PB",
    "TRE-PE",
    "TRE-PI",
    "TRE-PR",
    "TRE-RJ",
    "TRE-RN",
    "TRE-RO",
    "TRE-RR",
    "TRE-RS",
    "TRE-SC",
    "TRE-SE",
    "TRE-SP",
    "TRE-TO",
]


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
        return codes
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("tribunal_api_fetch_failed", error=str(exc))
        return []


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
