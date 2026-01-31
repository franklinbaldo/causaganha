import asyncio
import io
import json
import zipfile
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

import httpx
import structlog

from causaganha.config import settings
from causaganha.storage.djen_schema import (
    FIELD_CODIGO_CLASSE,
    FIELD_DATA_DISPONIBILIZACAO,
    FIELD_ID_ORGAO,
    FIELD_NOME_CLASSE,
    FIELD_NOME_ORGAO,
    FIELD_NUMERO_PROCESSO,
    FIELD_SIGLA_TRIBUNAL,
    FIELD_TIPO_COMUNICACAO,
    FIELD_TIPO_DOCUMENTO,
    get_field,
)
from causaganha.storage.repositories.intimation import store_intimations


logger = structlog.get_logger()

# Use the same proxy as the archive-zips workflow
DEFAULT_PROXY_URL = "https://djen-proxy-mhgmawcn3a-rj.a.run.app"


async def collect_metadata_for_court(
    tribunal: str,
    days_back: int = 1,
    proxy_url: str = DEFAULT_PROXY_URL,
) -> dict[str, Any]:
    """Collect metadata from DJEN Proxy for a specific court.

    This is the modern scraper that replaces the legacy direct-API version.
    It doesn't require selenium or complex integrations.
    """
    from causaganha.storage.connection import get_connection

    con = get_connection()

    # Calculate target dates
    today = date.today()
    target_dates = [(today - timedelta(days=i)).isoformat() for i in range(1, days_back + 1)]

    total_new = 0
    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for target_date in target_dates:
            logger.info("collecting_court_date", tribunal=tribunal, date=target_date)

            try:
                # 1. Get info from proxy
                info_url = f"{proxy_url}/api/v1/caderno/{tribunal}/{target_date}/D"
                response = await client.get(info_url)

                if response.status_code != 200:
                    logger.warning(
                        "caderno_not_available",
                        tribunal=tribunal,
                        date=target_date,
                        status=response.status_code,
                    )
                    continue

                info = response.json()
                download_url = info.get("url")

                if not download_url:
                    logger.warning("no_download_url", tribunal=tribunal, date=target_date)
                    continue

                # 2. Download ZIP
                logger.debug("downloading_zip", url=download_url)
                zip_response = await client.get(download_url, follow_redirects=True)

                if zip_response.status_code != 200:
                    logger.error("zip_download_failed", status=zip_response.status_code)
                    continue

                # 3. Extract JSON items
                intimations = []
                with zipfile.ZipFile(io.BytesIO(zip_response.content)) as zf:
                    for name in zf.namelist():
                        if name.endswith(".json"):
                            with zf.open(name) as f:
                                data = json.load(f)
                                items = data.get("items", [data] if "id" in data else [])
                                for item in items:
                                    if not isinstance(item, dict):
                                        continue

                                    # Wrap in a simple object for store_intimations
                                    obj = SimpleNamespace()
                                    obj.id = item.get("id")
                                    obj.numero_processo = get_field(item, FIELD_NUMERO_PROCESSO)
                                    obj.data_disponibilizacao = get_field(
                                        item,
                                        FIELD_DATA_DISPONIBILIZACAO,
                                    )
                                    obj.sigla_tribunal = get_field(item, FIELD_SIGLA_TRIBUNAL)
                                    obj.id_orgao = get_field(item, FIELD_ID_ORGAO)
                                    obj.tipo_comunicacao = get_field(item, FIELD_TIPO_COMUNICACAO)
                                    obj.nome_orgao = get_field(item, FIELD_NOME_ORGAO)
                                    obj.texto = item.get("texto")
                                    obj.link = item.get("link")
                                    obj.tipo_documento = get_field(item, FIELD_TIPO_DOCUMENTO)
                                    obj.nome_classe = get_field(item, FIELD_NOME_CLASSE)
                                    obj.codigo_classe = get_field(item, FIELD_CODIGO_CLASSE)
                                    obj.hash = item.get("hash")
                                    obj.status = item.get("status")

                                    intimations.append(obj)

                # 4. Store in DuckDB
                if intimations:
                    new_count = store_intimations(con, intimations)
                    total_new += new_count
                    results.append(
                        {"date": target_date, "count": len(intimations), "new": new_count},
                    )

            except Exception as e:
                logger.exception(
                    "collection_error",
                    tribunal=tribunal,
                    date=target_date,
                    error=str(e),
                )
                continue

    return {
        "status": "success",
        "tribunal": tribunal,
        "total_collected": total_new,
        "details": results,
    }


async def collect_metadata_for_all_courts(
    courts: list[str] | None = None,
    days_back: int = 1,
    max_concurrency: int = 5,
) -> None:
    """Collect for multiple courts in parallel.

    Uses a semaphore to limit concurrent requests to the proxy/API.
    """
    if not courts:
        courts = settings.COURTS

    logger.info(
        "starting_multi_court_collection",
        count=len(courts),
        days_back=days_back,
        concurrency=max_concurrency,
    )

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _collect_with_semaphore(court: str) -> None:
        async with semaphore:
            try:
                await collect_metadata_for_court(court, days_back)
            except Exception as e:
                logger.exception("court_parallel_collection_failed", court=court, error=str(e))

    await asyncio.gather(*[_collect_with_semaphore(court) for court in courts])
