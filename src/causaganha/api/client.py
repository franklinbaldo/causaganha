import httpx
import structlog
from datetime import date
from typing import Optional, List, Any

from pydantic import BaseModel, Field, ConfigDict

logger = structlog.get_logger()


class Advogado(BaseModel):
    """Lawyer model from PJe API."""

    numero_oab: str = Field(alias="numeroOab")
    uf_oab: str = Field(alias="ufOab")
    nome: str


class DestinarioAdvogado(BaseModel):
    """Lawyer destination wrapper."""
    advogado: Advogado


class Intimation(BaseModel):
    """PJe Intimation Model.

    Uses snake_case for internal fields, aliases for API CamelCase.
    """
    model_config = ConfigDict(populate_by_name=True)

    id: int
    numero_processo: str
    sigla_tribunal: str = Field(alias="siglaTribunal")
    # data_disponibilizacao appears as snake_case in mocks.
    # If API uses dataDisponibilizacao, we might need alias="dataDisponibilizacao".
    # But for now sticking to mock compliance.
    data_disponibilizacao: date

    link: Optional[str] = None
    tipo_comunicacao: Optional[str] = Field(None, alias="tipoComunicacao")
    nome_orgao: Optional[str] = Field(None, alias="nomeOrgao")
    texto: Optional[str] = None
    tipo_documento: Optional[str] = Field(None, alias="tipoDocumento")
    nome_classe: Optional[str] = Field(None, alias="nomeClasse")
    hash: Optional[str] = None
    status: Optional[str] = None

    numeroprocessocommascara: Optional[str] = None
    id_orgao: Optional[int] = None
    codigo_classe: Optional[str] = None
    destinarios: List[DestinarioAdvogado] = []


class PJeAPIClient:
    """Client for PJe Communications API."""

    def __init__(self, base_url: str = "https://comunicaapi.pje.jus.br/api/v1") -> None:
        self.base_url = base_url
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.client = httpx.AsyncClient(base_url=base_url, headers=headers, timeout=30.0)

    async def close(self) -> None:
        """Close the client."""
        await self.client.aclose()

    async def get_intimations_by_court(
        self,
        court: str,
        *,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
    ) -> List[Intimation]:
        """Fetch intimations for a court with optional date range."""
        params: dict[str, Any] = {"siglaTribunal": court}

        if data_inicio:
            params["dataDisponibilizacaoInicio"] = data_inicio.isoformat()
        if data_fim:
            params["dataDisponibilizacaoFim"] = data_fim.isoformat()

        all_intimations: List[Intimation] = []
        offset = 0

        while True:
            current_params = params.copy()
            if offset > 0:
                current_params["offset"] = offset

            logger.info("fetching_intimations", court=court, offset=offset)

            try:
                # Append 'comunicacao' to base_url
                response = await self.client.get("comunicacao", params=current_params)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logger.error("fetch_failed", error=str(e))
                raise

            items = data.get("items", [])
            count = data.get("count", 0)

            if not items:
                break

            for item in items:
                try:
                    all_intimations.append(Intimation(**item))
                except Exception as e:
                    logger.warning("parse_error", item_id=item.get("id"), error=str(e))

            # Stop if we fetched everything
            if len(all_intimations) >= count:
                break

            offset += len(items)

        return all_intimations
