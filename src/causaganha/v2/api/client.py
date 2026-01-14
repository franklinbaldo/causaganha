"""PJe Communications API client with httpx."""

import httpx
from pydantic import BaseModel, ConfigDict, Field


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
    hash: str | None = None
    status: str | None = None
    numero_processo: str | None = None
    data_disponibilizacao: str | None = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class PJeAPIClient:
    """Client for PJe Communications API.

    Handles authentication, pagination, and error handling.
    """

    def __init__(
        self,
        base_url: str = "https://comunicaapi.pje.jus.br/api/v1",
        timeout: int = 30,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: Base URL for the API.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=5),
        )

    async def get_intimations_by_court(
        self,
        sigla_tribunal: str,
        limit_per_page: int = 100,
    ) -> list[Intimation]:
        """Fetch all intimations for a court with automatic pagination.

        Args:
            sigla_tribunal: Court acronym (e.g. TJRO).
            limit_per_page: Items per page.

        Returns:
            List of Intimation objects.
        """
        all_intimations: list[Intimation] = []
        offset = 0

        while True:
            params = {
                "siglaTribunal": sigla_tribunal,
                "offset": offset,
                "limit": limit_per_page,
            }

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
