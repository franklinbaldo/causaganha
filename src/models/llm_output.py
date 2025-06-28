"""Pydantic models for structured LLM extraction output."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Decision(BaseModel):
    """Structured representation of a judicial decision."""

    numero_processo: str
    tipo_decisao: Optional[str] = None
    polo_ativo: List[str] = Field(default_factory=list)
    advogados_polo_ativo: List[str] = Field(default_factory=list)
    polo_passivo: List[str] = Field(default_factory=list)
    advogados_polo_passivo: List[str] = Field(default_factory=list)
    resultado: str
    data_decisao: date
    resumo: Optional[str] = None
    tribunal: Optional[str] = None


class ExtractionResult(BaseModel):
    """Container for all decisions extracted from a PDF."""

    file_name_source: str
    extraction_timestamp: datetime
    decisions: List[Decision]
    chunks_processed: int
    total_decisions_found: int
