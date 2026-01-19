"""PJe Communications API client with httpx."""

import asyncio
from datetime import date

import httpx
import structlog

from causaganha.domain.models import Intimation as DomainIntimation
from causaganha.domain.models import Lawyer, Party

from .schemas import Intimation as APIIntimation


logger = structlog.get_logger()


class PJeAPIClient:
    """Client for PJe Communications API.

    Handles authentication, pagination, and error handling
    """

    def __init__(
        self,
        base_url: str = "https://comunicaapi.pje.jus.br/api/v1",
        timeout: int = 30,
    ) -> None:
        """Initialize the API client."""
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=5),
        )

    def _map_to_domain(self, api_obj: APIIntimation) -> DomainIntimation:
        """Convert API DTO to Domain Entity."""
        # Convert date string to date object if needed, though Pydantic might handle it if passed as str
        # but let's be explicit if API returns "YYYY-MM-DD"

        # Note: APIIntimation.data_disponibilizacao is str. DomainIntimation.data_disponibilizacao is date.
        # Pydantic v2 handles str->date conversion automatically if ISO format.

        advogados = [
            Lawyer(
                id=d.advogado.id,
                nome=d.advogado.nome,
                numero_oab=d.advogado.numero_oab,
                uf_oab=d.advogado.uf_oab,
            )
            for d in api_obj.destinatarioadvogados
        ]

        partes = [Party(nome=p.nome, polo=p.polo) for p in api_obj.destinatarios]

        return DomainIntimation(
            id=api_obj.id,
            numero_processo=api_obj.numero_processo,
            numero_processo_formatado=api_obj.numeroprocessocommascara,
            data_disponibilizacao=api_obj.data_disponibilizacao,  # type: ignore
            sigla_tribunal=api_obj.sigla_tribunal,
            tipo_comunicacao=api_obj.tipo_comunicacao,
            nome_orgao=api_obj.nome_orgao,
            texto=api_obj.texto,
            link=api_obj.link,
            tipo_documento=api_obj.tipo_documento,
            nome_classe=api_obj.nome_classe,
            codigo_classe=api_obj.codigo_classe,
            hash=api_obj.hash,
            status=None,  # 'status' is not in the item schema
            advogados=advogados,
            partes=partes,
        )

    async def get_intimations_by_court(
        self,
        sigla_tribunal: str,
        data_disponibilizacao_inicio: date | None = None,
        data_disponibilizacao_fim: date | None = None,
        pagina: int = 1,
        itens_por_pagina: int = 100,
    ) -> list[DomainIntimation]:
        """Fetch all intimations for a court with automatic pagination.

        Args:
            sigla_tribunal: Court code (e.g., 'TJRO', 'TJMT')
            data_disponibilizacao_inicio: Start date filter
            data_disponibilizacao_fim: End date filter
            pagina: Page number to fetch
            itens_por_pagina: Results per page (max 100)

        Returns:
            List of validated DomainIntimation objects
        """
        all_domain_intimations: list[DomainIntimation] = []
        current_page = pagina

        while True:
            params: dict[str, str | int] = {
                "siglaTribunal": sigla_tribunal,
                "pagina": current_page,
                "itensPorPagina": itens_por_pagina,
            }

            if data_disponibilizacao_inicio:
                params["dataDisponibilizacaoInicio"] = data_disponibilizacao_inicio.strftime(
                    "%Y-%m-%d"
                )
            if data_disponibilizacao_fim:
                params["dataDisponibilizacaoFim"] = data_disponibilizacao_fim.strftime("%Y-%m-%d")

            logger.info(
                "fetching_page",
                tribunal=sigla_tribunal,
                pagina=current_page,
                itens_por_pagina=itens_por_pagina,
            )

            data = None
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    response = await self.client.get(
                        f"{self.base_url}/comunicacao",
                        params=params,
                    )
                    response.raise_for_status()
                    data = response.json()
                    break # Success

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        wait_time = 60 
                        logger.warning("rate_limit_hit", wait_seconds=wait_time, attempt=attempt+1)
                        await asyncio.sleep(wait_time)
                        if attempt == max_retries - 1:
                            logger.exception("api_request_failed_after_retries", error=str(e), params=params)
                            raise
                        continue
                    
                    if e.response.status_code >= 500:
                        wait_time = 5 * (attempt + 1)
                        logger.warning("server_error_retrying", wait_seconds=wait_time, attempt=attempt+1)
                        await asyncio.sleep(wait_time)
                        if attempt == max_retries - 1:
                            logger.exception("api_request_failed_after_retries", error=str(e), params=params)
                            raise
                        continue
                        
                    logger.exception("api_request_failed", error=str(e), params=params)
                    raise
                except httpx.RequestError as e:
                    logger.exception("api_request_failed", error=str(e), params=params)
                    raise

            # Validate and parse
            items = data.get("items", [])
            if not items:
                logger.info("no_more_items", total_fetched=len(all_domain_intimations))
                break

            try:
                # 1. Parse into API Schema (validates JSON structure)
                api_intimations = [APIIntimation(**item) for item in items]

                # 2. Map to Domain Entities
                domain_intimations = [self._map_to_domain(i) for i in api_intimations]

                all_domain_intimations.extend(domain_intimations)

                logger.info(
                    "page_fetched",
                    count=len(domain_intimations),
                    total=len(all_domain_intimations),
                )

            except Exception as e:
                logger.exception(
                    "validation_failed",
                    error=str(e),
                    sample=items[0] if items else None,
                )
                raise

            # Check if more pages based on items returned
            # If the API returns fewer items than requested, we're on the last page.
            if len(items) < itens_por_pagina:
                logger.info("last_page_fetched", total=len(all_domain_intimations))
                break

            current_page += 1

        return all_domain_intimations

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()