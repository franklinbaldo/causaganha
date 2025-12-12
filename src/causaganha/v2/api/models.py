"""Pydantic models for API responses"""

from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class LawyerInfo(BaseModel):
    """Lawyer information from API"""
    id: int
    nome: str
    numero_oab: str
    uf_oab: str

class DestinatarioAdvogado(BaseModel):
    """Lawyer association"""
    advogado: LawyerInfo

class Destinatario(BaseModel):
    """Party information"""
    nome: str
    polo: str  # 'A', 'P', etc.

class Intimation(BaseModel):
    """Complete intimation from API"""
    id: int
    numero_processo: str
    numeroprocessocommascara: Optional[str] = None
    data_disponibilizacao: str
    siglaTribunal: str = Field(alias='siglaTribunal')
    idOrgao: Optional[int] = Field(None, alias='idOrgao')
    tipoComunicacao: str = Field(alias='tipoComunicacao')
    nomeOrgao: str = Field(alias='nomeOrgao')
    texto: str
    link: str
    tipoDocumento: str = Field(alias='tipoDocumento')
    nomeClasse: str = Field(alias='nomeClasse')
    codigoClasse: Optional[str] = Field(None, alias='codigoClasse')
    hash: str
    status: str
    destinatarioadvogados: List[DestinatarioAdvogado] = []
    destinatarios: List[Destinatario] = []

    model_config = ConfigDict(populate_by_name=True)
