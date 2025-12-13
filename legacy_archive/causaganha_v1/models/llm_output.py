"""Pydantic models for structured LLM extraction output."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class Decision(BaseModel):
    """Structured representation of a judicial decision."""

    numero_processo: str
    tipo_decisao: str | None = None
    polo_ativo: list[str] = Field(default_factory=list)
    advogados_polo_ativo: list[str] = Field(default_factory=list)
    polo_passivo: list[str] = Field(default_factory=list)
    advogados_polo_passivo: list[str] = Field(default_factory=list)
    resultado: str
    data_decisao: date
    resumo: str | None = None
    tribunal: str | None = None


class ExtractionResult(BaseModel):
    """Container for all decisions extracted from a PDF."""

    file_name_source: str
    extraction_timestamp: datetime
    decisions: list[Decision]
    chunks_processed: int
    total_decisions_found: int
