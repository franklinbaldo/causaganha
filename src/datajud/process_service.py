"""Live per-process DataJud service for product surfaces.

This module deliberately sits above :mod:`datajud.client`: callers ask for a
CNJ in one tribunal and receive validated ``ProcessoCapa`` records across all
graus. HTTP/retry concerns stay in ``DataJudClient``; MCP presentation concerns
stay in ``causaganha_mcp.tools.datajud_processo``.
"""

from __future__ import annotations

import structlog
from pydantic import ValidationError

from datajud.client import DataJudClient
from datajud.dedup import dedup_capas
from datajud.models import ProcessoCapa, normalizar_cnj


log = structlog.get_logger()


async def consultar_processo(
    cnj: str,
    tribunal: str,
    *,
    request_timeout: float = 15.0,
    max_retries: int = 1,
    backoff_base: float = 1.0,
) -> list[ProcessoCapa]:
    """Consult one CNJ live in DataJud and return validated records for all graus.

    ``cnj`` is normalized before the request. Invalid input returns an empty
    list here because domain validation belongs to the public boundary; the MCP
    tool turns that condition into an actionable usage error before calling
    this service.
    """
    normalized = normalizar_cnj(cnj)
    if not normalized:
        return []

    async with DataJudClient(
        tribunal=tribunal,
        timeout=request_timeout,
        max_retries=max_retries,
        backoff_base=backoff_base,
        batch_size=1,
        batch_pause=0.0,
    ) as client:
        sources = await client.fetch_processos([normalized])

    capas: list[ProcessoCapa] = []
    for source in sources:
        try:
            capas.append(ProcessoCapa.from_source(source))
        except ValidationError as exc:
            log.warning(
                "datajud_live_process_malformed_document",
                numero_processo=source.get("numeroProcesso"),
                error=str(exc),
            )

    return dedup_capas(capas)
