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
        max_items: int | None = None,
        max_retries: int = 3,
        rate_limit_wait: float = 60.0,
        request_delay: float = 0.3,
    ) -> list[Intimation]:
        """Fetch all intimations for a court with automatic pagination.

        Args:
            sigla_tribunal: Court acronym (e.g. TJRO).
            limit_per_page: Items per page (max 100).
            data_inicio: Start date filter.
            data_fim: End date filter.
            max_items: Maximum total items to fetch (None = all).
            max_retries: Maximum retries on rate limit or server error.
            rate_limit_wait: Seconds to wait on 429 rate limit.
            request_delay: Seconds to wait between requests.

        Returns:
            List of Intimation objects.
        """
        import asyncio

        all_intimations: list[Intimation] = []
        offset = 0
        consecutive_errors = 0

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

            # Retry loop for rate limits and server errors
            for attempt in range(max_retries):
                try:
                    response = await self.client.get(
                        f"{self.base_url}/comunicacao",
                        params=params,
                    )

                    if response.status_code == 429:
                        # Rate limited - wait and retry
                        logger.warning(
                            "rate_limit_hit",
                            offset=offset,
                            attempt=attempt + 1,
                            wait_seconds=rate_limit_wait,
                        )
                        await asyncio.sleep(rate_limit_wait)
                        continue

                    if response.status_code >= 500:
                        # Server error - wait briefly and retry
                        wait_time = 5 * (attempt + 1)
                        logger.warning(
                            "server_error_retrying",
                            status=response.status_code,
                            attempt=attempt + 1,
                            wait_seconds=wait_time,
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    consecutive_errors = 0
                    break

                except httpx.HTTPStatusError as e:
                    if attempt == max_retries - 1:
                        logger.error(
                            "api_request_failed_after_retries",
                            offset=offset,
                            error=str(e),
                        )
                        # Return what we have so far instead of failing completely
                        if all_intimations:
                            logger.warning(
                                "returning_partial_results",
                                fetched=len(all_intimations),
                            )
                            return all_intimations
                        raise

                except httpx.RequestError as e:
                    consecutive_errors += 1
                    if consecutive_errors >= max_retries:
                        logger.error(
                            "too_many_consecutive_errors",
                            offset=offset,
                            error=str(e),
                        )
                        if all_intimations:
                            return all_intimations
                        raise
                    await asyncio.sleep(5)
                    continue
            else:
                # All retries exhausted
                logger.error("max_retries_exhausted", offset=offset)
                if all_intimations:
                    return all_intimations
                raise RuntimeError(f"Failed to fetch data at offset {offset}")

            data = response.json()

            items = data.get("items", [])
            if not items:
                logger.info("no_more_items", total_fetched=len(all_intimations))
                break

            intimations = [Intimation(**item) for item in items]
            all_intimations.extend(intimations)

            total_count = data.get("count", 0)

            logger.debug(
                "page_fetched",
                offset=offset,
                page_items=len(intimations),
                total_fetched=len(all_intimations),
                api_total=total_count,
            )

            # Check limits
            if max_items and len(all_intimations) >= max_items:
                logger.info("max_items_reached", max_items=max_items)
                break

            if len(all_intimations) >= total_count:
                logger.info("all_items_fetched", total=len(all_intimations))
                break

            offset += limit_per_page

            # Polite delay between requests
            if request_delay > 0:
                await asyncio.sleep(request_delay)

        return all_intimations

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
