"""Domain entities for CausaGanha."""

from datetime import date
from typing import List, Optional

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
    numero_processo_formatado: Optional[str] = None
    data_disponibilizacao: date
    sigla_tribunal: str
    id_orgao: Optional[int] = None
    tipo_comunicacao: str
    nome_orgao: str
    texto: str
    link: Optional[str] = None  # TDD: Some intimations may not have download links
    tipo_documento: str
    nome_classe: str
    codigo_classe: Optional[str] = None
    hash: str
    status: str

    # Relationships
    advogados: List[Lawyer] = Field(default_factory=list)
    partes: List[Party] = Field(default_factory=list)
