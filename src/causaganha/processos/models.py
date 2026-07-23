"""Modelos de domínio para o dossiê de processo unificado (RFC 0014 M2).

Dataclasses puras, sem Pydantic — a mesma separação usada em
`datajud.service`/`tjro_juris.service`/etc.: a camada de serviço não conhece
FastMCP nem a CLI, só o domínio. `causaganha_mcp.tools.processo` converte
este resultado para os modelos Pydantic da tool.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class CnjInvalidoError(ValueError):
    """O CNJ informado não tem 20 dígitos válidos."""


@dataclass
class FonteCobertura:
    """Estado de uma fonte na geração do dataset (de `indice_processual.report.json`)."""

    fonte: str
    status: str
    registros: int


@dataclass
class DocumentoProcesso:
    """Documento JURIS ou STJ do processo (nunca DJEN/DataJud — ver `service.buscar_processo`)."""

    fonte: str
    id_documento: str
    tipo: str | None
    data: str | None
    url: str | None
    resumo: str | None


@dataclass
class DjenResumo:
    """Resumo das publicações DJEN de um processo."""

    primeira_publicacao: str | None
    ultima_publicacao: str | None
    n_publicacoes: int | None
    tribunais: list[str]


@dataclass
class JurisDecisao:
    """Decisão(ões) do TJRO JURIS para um processo."""

    n_documentos: int | None
    tipos: list[str]
    data_julgamento: str | None
    orgao: str | None
    relator: str | None
    classe: str | None
    url: str | None


@dataclass
class StjAcordao:
    """Acórdão do STJ para um processo, quando houver."""

    id: str | None
    classe: str | None
    relator: str | None
    tema: str | None
    tese: str | None
    ementa: str | None
    data_decisao: str | None
    data_publicacao: str | None


@dataclass
class DatajudCapa:
    """Capa oficial do DataJud (RFC 0010) para um processo."""

    classe_oficial: str | None
    assuntos: str | None
    orgao_julgador: str | None
    grau: str | None
    data_ajuizamento: str | None
    ultima_atualizacao: str | None


@dataclass
class ProcessoConsultaResult:
    """Resultado de `service.buscar_processo` — encontrado ou não."""

    encontrado: bool
    nr_processo: str
    nr_processo_mascara: str
    fontes_presentes: list[str] = field(default_factory=list)
    cobertura_dataset: list[FonteCobertura] = field(default_factory=list)
    djen: DjenResumo | None = None
    juris: JurisDecisao | None = None
    stj: StjAcordao | None = None
    datajud: DatajudCapa | None = None
    documentos: list[DocumentoProcesso] = field(default_factory=list)
    documentos_truncados: bool = False
    dataset_gerado_em: str | None = None
    avisos: list[str] = field(default_factory=list)
