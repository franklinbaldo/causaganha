from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LawyerInfo(BaseModel):
    """Lawyer information from API."""

    id: int
    nome: str
    numero_oab: str
    uf_oab: str


class DestinatarioAdvogado(BaseModel):
    """Lawyer association wrapper."""

    advogado: LawyerInfo


class Destinatario(BaseModel):
    """Party information."""

    nome: str
    polo: str  # 'A', 'P', etc.


class Intimation(BaseModel):
    """Complete intimation from API."""

    id: int
    numero_processo: str
    numeroprocessocommascara: Optional[str] = None
    data_disponibilizacao: str
    sigla_tribunal: str = Field(alias="siglaTribunal")
    id_orgao: Optional[int] = Field(None, alias="idOrgao")
    tipo_comunicacao: Optional[str] = Field(None, alias="tipoComunicacao")
    nome_orgao: Optional[str] = Field(None, alias="nomeOrgao")
    texto: Optional[str] = None
    link: Optional[str] = None
    tipo_documento: Optional[str] = Field(None, alias="tipoDocumento")
    nome_classe: Optional[str] = Field(None, alias="nomeClasse")
    codigo_classe: Optional[str] = Field(None, alias="codigoClasse")
    hash: Optional[str] = None
    status: Optional[str] = None
    destinatarioadvogados: List[DestinatarioAdvogado] = []
    destinatarios: List[Destinatario] = []

    model_config = ConfigDict(populate_by_name=True)
