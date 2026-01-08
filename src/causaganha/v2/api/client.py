"""PJe Communications API client with httpx"""

import httpx
import structlog
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field

logger = structlog.get_logger()

# Pydantic models for API responses
class LawyerInfo(BaseModel):
    """Lawyer information from API"""
    id: int
    nome: str
    numero_oab: str
    uf_oab: str

class DestinarioAdvogado(BaseModel):
    """Lawyer association"""
    advogado: LawyerInfo

class Destinatario(BaseModel):
    """Party information"""
    nome: str
    polo: str  # 'A', 'P', etc.

class Intimation(BaseModel):
    """Complete intimation from API"""
    id: int
    numero_processo: str
    numeroprocessocommascara: Optional[str] = None
    data_disponibilizacao: str
    siglaTribunal: str = Field(alias='siglaTribunal')
    idOrgao: Optional[int] = Field(None, alias='idOrgao')
    tipoComunicacao: str = Field(alias='tipoComunicacao')
    nomeOrgao: str = Field(alias='nomeOrgao')
    texto: str
    link: str
    tipoDocumento: str = Field(alias='tipoDocumento')
    nomeClasse: str = Field(alias='nomeClasse')
    codigoClasse: Optional[str] = Field(None, alias='codigoClasse')
    hash: str
    status: str
    destinatarioadvogados: List[DestinarioAdvogado] = []
    destinatarios: List[Destinatario] = []

    class Config:
        populate_by_name = True

class PJeAPIClient:
    """
    Client for PJe Communications API

    Handles authentication, pagination, and error handling
    """

    def __init__(
        self,
        base_url: str = "https://comunicaapi.pje.jus.br/api/v1",
        timeout: int = 30
    ):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=5)
        )

    async def get_intimations_by_court(
        self,
        sigla_tribunal: str,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        limit_per_page: int = 100
    ) -> List[Intimation]:
        """
        Fetch all intimations for a court with automatic pagination

        Args:
            sigla_tribunal: Court code (e.g., 'TJRO', 'TJMT')
            data_inicio: Start date filter
            data_fim: End date filter
            limit_per_page: Results per page (max 100)

        Returns:
            List of validated Intimation objects
        """
        all_intimations = []
        offset = 0

        while True:
            params = {
                "siglaTribunal": sigla_tribunal,
                "offset": offset,
                "limit": limit_per_page
            }

            if data_inicio:
                params["dataInicio"] = data_inicio.strftime("%Y-%m-%d")
            if data_fim:
                params["dataFim"] = data_fim.strftime("%Y-%m-%d")

            logger.info("fetching_page",
                       tribunal=sigla_tribunal,
                       offset=offset,
                       limit=limit_per_page)

            try:
                response = await self.client.get(
                    f"{self.base_url}/comunicacao",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

            except httpx.HTTPError as e:
                logger.error("api_request_failed",
                            error=str(e),
                            params=params)
                raise

            # Validate and parse
            items = data.get("items", [])
            if not items:
                logger.info("no_more_items", total_fetched=len(all_intimations))
                break

            try:
                intimations = [Intimation(**item) for item in items]
                all_intimations.extend(intimations)
                logger.info("page_fetched",
                           count=len(intimations),
                           total=len(all_intimations))

            except Exception as e:
                logger.error("validation_failed",
                            error=str(e),
                            sample=items[0] if items else None)
                raise

            # Check if more pages
            total_count = data.get("count", 0)
            if len(all_intimations) >= total_count:
                logger.info("all_pages_fetched",
                           total=len(all_intimations))
                break

            offset += limit_per_page

        return all_intimations

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
