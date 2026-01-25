import asyncio
import io
import json
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
import structlog

from causaganha.config import settings
from causaganha.storage.queries import store_intimations

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
                    logger.warning("caderno_not_available", tribunal=tribunal, date=target_date, status=response.status_code)
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
                                    # Wrap in a simple object for store_intimations
                                    # Using a simple class to support dot access
                                    class Item:
                                        def __init__(self, d):
                                            self.__dict__.update(d)
                                            # Fix field names for V2 schema if necessary
                                            self.id = d.get("id")
                                            self.numero_processo = d.get("numero_processo") or d.get("numeroProcesso")
                                            self.data_disponibilizacao = d.get("data_disponibilizacao") or d.get("dataDisponibilizacao")
                                            self.sigla_tribunal = d.get("sigla_tribunal") or d.get("siglaTribunal")
                                            self.id_orgao = d.get("id_orgao") or d.get("idOrgao")
                                            self.tipo_comunicacao = d.get("tipo_comunicacao") or d.get("tipoComunicacao")
                                            self.nome_orgao = d.get("nome_orgao") or d.get("nomeOrgao")
                                            self.texto = d.get("texto")
                                            self.link = d.get("link")
                                            self.tipo_documento = d.get("tipo_documento") or d.get("tipoDocumento")
                                            self.nome_classe = d.get("nome_classe") or d.get("nomeClasse")
                                            self.codigo_classe = d.get("codigo_classe") or d.get("codigoClasse")
                                            self.hash = d.get("hash")
                                            self.status = d.get("status")

                                    intimations.append(Item(item))
                
                # 4. Store in DuckDB
                if intimations:
                    new_count = store_intimations(con, intimations)
                    total_new += new_count
                    results.append({"date": target_date, "count": len(intimations), "new": new_count})
                
            except Exception as e:
                logger.exception("collection_error", tribunal=tribunal, date=target_date, error=str(e))
                continue
                
    return {
        "status": "success",
        "tribunal": tribunal,
        "total_collected": total_new,
        "details": results
    }

async def collect_metadata_for_all_courts(
    courts: list[str] | None = None,
    days_back: int = 1,
) -> None:
    """Collect for multiple courts."""
    if not courts:
        courts = settings.COURTS
        
    logger.info("starting_multi_court_collection", count=len(courts), days_back=days_back)
    
    for court in courts:
        await collect_metadata_for_court(court, days_back)
