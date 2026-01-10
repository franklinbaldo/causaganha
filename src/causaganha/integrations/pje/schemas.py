"""Pydantic models for API responses."""


from pydantic import BaseModel, ConfigDict, Field


class LawyerInfo(BaseModel):
    """Lawyer information from API."""

    id: int
    nome: str
    numero_oab: str
    uf_oab: str


class DestinatarioAdvogado(BaseModel):
    """Lawyer association."""

    advogado: LawyerInfo


class Destinatario(BaseModel):
    """Party information."""

    nome: str
    polo: str  # 'A', 'P', etc.


class Intimation(BaseModel):
    """Complete intimation from API, aligned with OpenAPI spec."""

    id: int
    data_disponibilizacao: str
    sigla_tribunal: str = Field(alias="siglaTribunal")
    tipo_comunicacao: str = Field(alias="tipoComunicacao")
    nome_orgao: str = Field(alias="nomeOrgao")
    texto: str
    numero_processo: str
    meio: str
    link: str
    tipo_documento: str = Field(alias="tipoDocumento")
    nome_classe: str = Field(alias="nomeClasse")
    codigo_classe: str | None = Field(None, alias="codigoClasse")
    numero_comunicacao: int | None = Field(None, alias="numeroComunicacao")
    ativo: bool
    hash: str
    datadisponibilizacao: str  # This is a datetime string
    meiocompleto: str
    numeroprocessocommascara: str | None = None
    destinatarios: list[Destinatario] = []
    destinatarioadvogados: list[DestinatarioAdvogado] = []
    # Note: 'status' is in the top-level response, not in each 'item'
    # According to the spec. Removing from here.

    model_config = ConfigDict(populate_by_name=True)
