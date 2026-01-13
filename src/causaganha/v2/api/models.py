"""Pydantic models for PJe API responses."""


from pydantic import BaseModel, ConfigDict, Field


class LawyerInfo(BaseModel):
    """Lawyer information from API."""

    id: int
    nome: str
    numero_oab: str
    uf_oab: str


class DestinarioAdvogado(BaseModel):
    """Lawyer association."""

    advogado: LawyerInfo


class Destinatario(BaseModel):
    """Party information."""

    nome: str
    polo: str  # 'A', 'P', etc.


class Intimation(BaseModel):
    """Complete intimation from API."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    numero_processo: str
    numeroprocessocommascara: str | None = None
    data_disponibilizacao: str
    sigla_tribunal: str = Field(alias="siglaTribunal")
    id_orgao: int | None = Field(None, alias="idOrgao")
    tipo_comunicacao: str = Field(alias="tipoComunicacao")
    nome_orgao: str = Field(alias="nomeOrgao")
    texto: str
    link: str
    tipo_documento: str = Field(alias="tipoDocumento")
    nome_classe: str = Field(alias="nomeClasse")
    codigo_classe: str | None = Field(None, alias="codigoClasse")
    hash: str
    status: str
    destinatarioadvogados: list[DestinarioAdvogado] = []
    destinatarios: list[Destinatario] = []
