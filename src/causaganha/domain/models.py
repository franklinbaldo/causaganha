"""Domain entities for CausaGanha."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class Lawyer(BaseModel):
    """Represents a lawyer in the domain."""

    id: int
    nome: str
    numero_oab: str
    uf_oab: str


class Party(BaseModel):
    """Represents a party involved in a case."""

    nome: str
    polo: str  # 'A' for Active (Plaintiff), 'P' for Passive (Defendant)


class Intimation(BaseModel):
    """Represents a judicial intimation."""

    id: int
    numero_processo: str
    numero_processo_formatado: str | None = None
    data_disponibilizacao: date
    sigla_tribunal: str
    id_orgao: int | None = None
    tipo_comunicacao: str
    nome_orgao: str
    texto: str
    link: str | None = None  # TDD: Some intimations may not have download links
    tipo_documento: str
    nome_classe: str
    codigo_classe: str | None = None
    hash: str
    status: str | None = None

    # Relationships
    advogados: list[Lawyer] = Field(default_factory=list)
    partes: list[Party] = Field(default_factory=list)

    # Pipeline tracking
    analyzed: bool = False
    analysis_attempted_at: datetime | None = None
    analysis_error: str | None = None
    analyzed_at: datetime | None = None
    ia_url: str | None = None
    archived_at: datetime | None = None
    needs_download: bool = True
