"""PJe Communications API client with httpx."""

from datetime import date
from typing import List

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
                uf_oab=d.advogado.uf_oab
            )
            for d in api_obj.destinatarioadvogados
        ]

        partes = [
            Party(nome=p.nome, polo=p.polo)
            for p in api_obj.destinatarios
        ]

        return DomainIntimation(
            id=api_obj.id,
            numero_processo=api_obj.numero_processo,
            numero_processo_formatado=api_obj.numeroprocessocommascara,
            data_disponibilizacao=api_obj.data_disponibilizacao, # type: ignore (Pydantic will parse)
            sigla_tribunal=api_obj.siglaTribunal,
            id_orgao=api_obj.idOrgao,
            tipo_comunicacao=api_obj.tipoComunicacao,
            nome_orgao=api_obj.nomeOrgao,
            texto=api_obj.texto,
            link=api_obj.link,
            tipo_documento=api_obj.tipoDocumento,
            nome_classe=api_obj.nomeClasse,
            codigo_classe=api_obj.codigoClasse,
            hash=api_obj.hash,
            status=api_obj.status,
            advogados=advogados,
            partes=partes
        )

    async def get_intimations_by_court(
        self,
        sigla_tribunal: str,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        limit_per_page: int = 100,
    ) -> List[DomainIntimation]:
        """Fetch all intimations for a court with automatic pagination.

        Args:
            sigla_tribunal: Court code (e.g., 'TJRO', 'TJMT')
            data_inicio: Start date filter
            data_fim: End date filter
            limit_per_page: Results per page (max 100)

        Returns:
            List of validated DomainIntimation objects
        """
        all_domain_intimations: List[DomainIntimation] = []
        offset = 0

        while True:
            params: dict[str, str | int] = {
                "siglaTribunal": sigla_tribunal,
                "offset": offset,
                "limit": limit_per_page,
            }

            if data_inicio:
                params["dataInicio"] = data_inicio.strftime("%Y-%m-%d")
            if data_fim:
                params["dataFim"] = data_fim.strftime("%Y-%m-%d")

            logger.info(
                "fetching_page",
                tribunal=sigla_tribunal,
                offset=offset,
                limit=limit_per_page,
            )

            try:
                response = await self.client.get(
                    f"{self.base_url}/comunicacao",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()

            except httpx.HTTPError as e:
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

            # Check if more pages
            total_count = data.get("count", 0)
            if len(all_domain_intimations) >= total_count:
                logger.info("all_pages_fetched", total=len(all_domain_intimations))
                break

            offset += limit_per_page

        return all_domain_intimations

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
