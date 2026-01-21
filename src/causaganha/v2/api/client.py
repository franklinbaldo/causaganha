"""PJe Communications API client with httpx."""

import os
import httpx
from datetime import date
from pydantic import BaseModel, ConfigDict, Field
import structlog

logger = structlog.get_logger()


class LawyerInfo(BaseModel):
    """Lawyer information from API."""

    id: int
    nome: str
    numero_oab: str
    uf_oab: str


class DestinarioAdvogado(BaseModel):
    """Lawyer association."""

    advogado: LawyerInfo


class Destinatario(BaseModel):
    """Party information."""

    nome: str
    polo: str  # 'A', 'P', etc.


class Intimation(BaseModel):
    """PJe Intimation Model."""

    id: int
    sigla_tribunal: str = Field(alias="siglaTribunal")
    tipo_comunicacao: str | None = Field(default=None, alias="tipoComunicacao")
    nome_orgao: str | None = Field(default=None, alias="nomeOrgao")
    texto: str | None = None
    link: str | None = None
    tipo_documento: str | None = Field(default=None, alias="tipoDocumento")
    nome_classe: str | None = Field(default=None, alias="nomeClasse")
    codigo_classe: str | None = Field(default=None, alias="codigoClasse")
    id_orgao: int | None = Field(default=None, alias="idOrgao")
    hash: str | None = None
    status: str | None = None
    numero_processo: str | None = None
    data_disponibilizacao: str | None = None
    numeroprocessocommascara: str | None = None
    destinatarioadvogados: list[DestinarioAdvogado] = []
    destinatarios: list[Destinatario] = []

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class PJeAPIClient:
    """Client for PJe Communications API.

    Handles authentication, pagination, and error handling.

    Auto-detects geo-blocking bypass proxy if DJEN_PROXY_URL is set.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int = 30,
        use_proxy: bool | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: Base URL for the API. If None, auto-detects proxy or uses default.
            timeout: Request timeout in seconds.
            use_proxy: Force proxy usage (True) or disable (False). None = auto-detect.
        """
        # Auto-detect proxy configuration
        proxy_url = os.getenv("DJEN_PROXY_URL")
        proxy_api_key = os.getenv("DJEN_PROXY_API_KEY")

        # Determine if we should use proxy
        if use_proxy is None:
            # Auto-detect: use proxy if DJEN_PROXY_URL is set
            use_proxy = proxy_url is not None

        if use_proxy and proxy_url:
            # Use proxy
            self.base_url = proxy_url
            self.using_proxy = True

            # Set up headers with API key if provided
            headers = {}
            if proxy_api_key:
                headers["X-API-Key"] = proxy_api_key

            self.client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(max_keepalive_connections=5),
                headers=headers,
            )

            logger.info(
                "pje_client_initialized_with_proxy",
                proxy_url=proxy_url,
                has_api_key=bool(proxy_api_key),
            )
        else:
            # Direct connection to DJEN API
            self.base_url = base_url or "https://comunicaapi.pje.jus.br/api/v1"
            self.using_proxy = False

            self.client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(max_keepalive_connections=5),
            )

            logger.info(
                "pje_client_initialized_direct",
                base_url=self.base_url,
            )

    async def get_intimations_by_court(
        self,
        sigla_tribunal: str,
        limit_per_page: int = 100,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> list[Intimation]:
        """Fetch all intimations for a court with automatic pagination.

        Args:
            sigla_tribunal: Court acronym (e.g. TJRO).
            limit_per_page: Items per page.
            data_inicio: Start date filter.
            data_fim: End date filter.

        Returns:
            List of Intimation objects.
        """
        all_intimations: list[Intimation] = []
        offset = 0

        while True:
            params: dict[str, str | int] = {
                "siglaTribunal": sigla_tribunal,
                "offset": offset,
                "limit": limit_per_page,
            }

            if data_inicio:
                params["dataDisponibilizacaoInicio"] = data_inicio.isoformat()
            if data_fim:
                params["dataDisponibilizacaoFim"] = data_fim.isoformat()

            response = await self.client.get(
                f"{self.base_url}/comunicacao",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if not items:
                break

            intimations = [Intimation(**item) for item in items]
            all_intimations.extend(intimations)

            total_count = data.get("count", 0)
            if len(all_intimations) >= total_count:
                break

            offset += limit_per_page

        return all_intimations

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
