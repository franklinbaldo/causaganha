"""Pydantic models for API responses"""


from pydantic import BaseModel, ConfigDict, Field


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
    numeroprocessocommascara: str | None = None
    data_disponibilizacao: str
    siglaTribunal: str = Field(alias="siglaTribunal")
    idOrgao: int | None = Field(None, alias="idOrgao")
    tipoComunicacao: str = Field(alias="tipoComunicacao")
    nomeOrgao: str = Field(alias="nomeOrgao")
    texto: str
    link: str
    tipoDocumento: str = Field(alias="tipoDocumento")
    nomeClasse: str = Field(alias="nomeClasse")
    codigoClasse: str | None = Field(None, alias="codigoClasse")
    hash: str
    status: str
    destinatarioadvogados: list[DestinatarioAdvogado] = []
    destinatarios: list[Destinatario] = []

    model_config = ConfigDict(populate_by_name=True)
