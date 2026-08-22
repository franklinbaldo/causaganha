"""Modelos de domínio da busca de publicações arquivadas."""

from __future__ import annotations

from dataclasses import dataclass, field


class PublicacoesError(RuntimeError):
    """Erro base da consulta ao arquivo de publicações."""


class CriteriosInvalidosError(PublicacoesError):
    """A consulta não possui critérios suficientes ou contém valor inválido."""


class CatalogoIndisponivelError(PublicacoesError):
    """O catálogo canônico do CausaGanha não pôde ser consultado."""


class AcervoIndisponivelError(PublicacoesError):
    """Os Parquets necessários para executar a consulta ficaram indisponíveis."""


@dataclass(frozen=True)
class PublicacoesQuery:
    """Critérios semânticos de busca, independentes do schema físico do arquivo."""

    processo: str | None = None
    oab: str | None = None
    uf_oab: str | None = None
    parte: str | None = None
    advogado: str | None = None
    texto: str | None = None
    tribunal: str | None = None
    data_inicio: str | None = None
    data_fim: str | None = None
    incluir_trecho: bool = False
    limite: int = 10
    pagina: int = 1


@dataclass(frozen=True)
class PublicacaoArquivo:
    """Uma comunicação DJEN preservada no arquivo do CausaGanha."""

    id: str
    data: str | None
    tribunal: str | None
    tipo: str | None
    orgao: str | None
    numero_processo: str | None
    numero_processo_mascara: str | None
    link: str | None
    tipo_documento: str | None
    classe: str | None
    trecho: str | None
    ia_item: str | None


@dataclass(frozen=True)
class CoberturaArquivo:
    """Qualificação da cobertura conhecida para o escopo consultado."""

    status: str
    lacunas_conhecidas: int | None
    arquivos_consultados: int
    itens_consultados: int
    aviso: str | None = None


@dataclass(frozen=True)
class PublicacoesBusca:
    """Resultado semântico de uma busca no arquivo DJEN do CausaGanha."""

    resultados: list[PublicacaoArquivo]
    total_encontrado: int
    pagina: int
    limite: int
    resultados_truncados: bool
    cobertura: CoberturaArquivo
    criterios: dict[str, str | bool | int | None]
    consultado_em: str
    avisos: list[str] = field(default_factory=list)
