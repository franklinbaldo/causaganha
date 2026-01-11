"""Domain entities for CausaGanha."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from causaganha.analysis.models import DecisionAnalysis


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


class AnalysisResult(BaseModel):
    """Result of an analysis."""
    intimation_id: int
    analysis: DecisionAnalysis
    analyzed_at: datetime
    scored: bool = False
    id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        data = self.analysis.model_dump(exclude={"acordao", "tribunal", "decision_date"})
        data["intimation_id"] = self.intimation_id
        data["analyzed_at"] = self.analyzed_at
        data["scored"] = self.scored
        if self.id:
            data["id"] = self.id
        return data
