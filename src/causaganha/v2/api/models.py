"""Pydantic models for PJe API responses."""

from typing import List, Optional
from pydantic import BaseModel, Field

class LawyerInfo(BaseModel):
    """Lawyer information from API."""
    id: int
    nome: str
    numero_oab: str
    uf_oab: str

class DestinarioAdvogado(BaseModel):
    """Lawyer association wrapper."""
    advogado: LawyerInfo

class Destinatario(BaseModel):
    """Party information."""
    nome: str
    polo: str

class Intimation(BaseModel):
    """Complete intimation from PJe API."""
    id: int
    numero_processo: str
    numeroprocessocommascara: Optional[str] = None
    data_disponibilizacao: str
    siglaTribunal: str = Field(alias='siglaTribunal')
    idOrgao: Optional[int] = Field(None, alias='idOrgao')
    tipoComunicacao: str = Field(alias='tipoComunicacao')
    nomeOrgao: str = Field(alias='nomeOrgao')
    texto: str
    link: Optional[str] = None  # Make link optional as seen in tests
    tipoDocumento: str = Field(alias='tipoDocumento')
    nomeClasse: str = Field(alias='nomeClasse')
    codigoClasse: Optional[str] = Field(None, alias='codigoClasse')
    hash: str
    status: str
    destinatarioadvogados: List[DestinarioAdvogado] = []
    destinatarios: List[Destinatario] = []

    model_config = {
        "populate_by_name": True
    }
