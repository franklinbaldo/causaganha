"""Type definitions for the pipeline module."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CollectedIntimation(BaseModel):
    """Represents a single intimation collected from DJEN."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: int | str
    numero_processo: str | None = None
    data_disponibilizacao: str | None = None
    sigla_tribunal: str | None = None
    id_orgao: int | str | None = None
    tipo_comunicacao: str | None = None
    nome_orgao: str | None = None
    texto: str | None = None
    link: str | None = None
    tipo_documento: str | None = None
    nome_classe: str | None = None
    codigo_classe: int | str | None = None
    hash: str | None = None
    status: str | None = None

    # Allow extra fields for flexibility during initial collection
    # but store them only if defined above.
