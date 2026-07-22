"""Pydantic models and normalization helpers for DataJud documents.

The API returns Elasticsearch hits whose ``_source`` carries the process
"capa" (classe, assuntos, órgão julgador, grau, datas, sigilo) plus the
``movimentos`` array (tabelas processuais unificadas do CNJ). Codes and
names from the CNJ tables are preserved verbatim.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# CNJ normalization moved to causaganha.processos.cnj (RFC 0014 M2) — a
# shared module usable by non-DataJud consumers (the process-reconciliation
# pipeline, the processo_consultar MCP tool). Reexported here so existing
# `from datajud.models import normalizar_cnj` call sites keep working.
from causaganha.processos.cnj import CNJ_LEN, formatar_cnj, normalizar_cnj, so_digitos


__all__ = [
    "CNJ_LEN",
    "CodigoNome",
    "ComplementoTabelado",
    "Movimento",
    "ProcessoCapa",
    "data14_bound",
    "formatar_cnj",
    "normalizar_cnj",
    "normalizar_data14",
    "so_digitos",
]

# ``dataAjuizamento`` is a 14-digit string (AAAAMMDDHHMMSS); some records
# truncate the time part, so hour/minute/second groups are optional.
_DATA14_RE = re.compile(r"(\d{4})(\d{2})(\d{2})(\d{2})?(\d{2})?(\d{2})?")
_DATE_BR_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
_DATE_ISO_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def normalizar_data14(value: str | None) -> str | None:
    """Normalize a 14-digit DataJud date (AAAAMMDDHHMMSS) to ISO-8601.

    Accepts truncated values (date-only or date+hour+minute) and pads the
    missing time components with zeros. Returns None when *value* does not
    start with an 8-digit date.
    """
    raw = (value or "").strip()
    match = _DATA14_RE.match(raw)
    if not match:
        return None
    ano, mes, dia, hh, mm, ss = match.groups()
    return f"{ano}-{mes}-{dia}T{hh or '00'}:{mm or '00'}:{ss or '00'}"


def data14_bound(value: str, *, fim: bool = False) -> str:
    """Convert DD/MM/AAAA or AAAA-MM-DD to a 14-digit range bound.

    Range queries on ``dataAjuizamento`` compare 14-digit strings, so a bound
    must cover the whole day: 000000 for the start, 235959 for the end.
    """
    raw = value.strip()
    match_br = _DATE_BR_RE.match(raw)
    if match_br:
        base = f"{match_br.group(3)}{match_br.group(2)}{match_br.group(1)}"
    else:
        match_iso = _DATE_ISO_RE.match(raw)
        base = (
            f"{match_iso.group(1)}{match_iso.group(2)}{match_iso.group(3)}"
            if match_iso
            else so_digitos(raw)[:8]
        )
    base = (base + "0" * 8)[:8]
    return base + ("235959" if fim else "000000")


class CodigoNome(BaseModel):
    """A tabled (codigo, nome) pair from the CNJ unified tables."""

    model_config = ConfigDict(populate_by_name=True)

    codigo: int | None = None
    nome: str | None = None


class ComplementoTabelado(BaseModel):
    """A tabled complement attached to a movimento."""

    model_config = ConfigDict(populate_by_name=True)

    codigo: int | None = None
    valor: int | None = None
    nome: str | None = None
    descricao: str | None = None


class Movimento(BaseModel):
    """A single entry in the process movement line."""

    model_config = ConfigDict(populate_by_name=True)

    codigo: int | None = None
    nome: str | None = None
    data_hora: str | None = Field(default=None, alias="dataHora")
    complementos_tabelados: list[ComplementoTabelado] = Field(
        default_factory=list, alias="complementosTabelados"
    )

    @field_validator("complementos_tabelados", mode="before")
    @classmethod
    def _none_as_empty(cls, value: Any) -> Any:  # noqa: ANN401 — pydantic pre-validator
        return value if value is not None else []

    def complementos_str(self) -> str:
        """Render tabled complements as 'descricao=nome; …' for the parquet."""
        parts = [f"{c.descricao or ''}={c.nome}" for c in self.complementos_tabelados if c.nome]
        return "; ".join(parts)


class ProcessoCapa(BaseModel):
    """Capa de um processo em um grau — um documento do índice DataJud.

    The same CNJ appears in separate documents per grau/órgão; the natural
    key is ``(numeroProcesso, grau, orgaoJulgador.codigo)`` (see dedup.py).
    """

    model_config = ConfigDict(populate_by_name=True)

    numero_processo: str = Field(alias="numeroProcesso")
    tribunal: str = ""
    grau: str = ""
    classe: CodigoNome = Field(default_factory=CodigoNome)
    assuntos: list[CodigoNome] = Field(default_factory=list)
    orgao_julgador: CodigoNome = Field(default_factory=CodigoNome, alias="orgaoJulgador")
    sistema: CodigoNome = Field(default_factory=CodigoNome)
    formato: CodigoNome = Field(default_factory=CodigoNome)
    nivel_sigilo: int | None = Field(default=None, alias="nivelSigilo")
    data_ajuizamento: str | None = Field(default=None, alias="dataAjuizamento")
    data_hora_ultima_atualizacao: str | None = Field(
        default=None, alias="dataHoraUltimaAtualizacao"
    )
    movimentos: list[Movimento] = Field(default_factory=list)

    @field_validator("assuntos", "movimentos", mode="before")
    @classmethod
    def _flatten_lists(cls, value: Any) -> Any:  # noqa: ANN401 — pydantic pre-validator
        """Tolerate None and one level of list nesting (seen in some tribunals)."""
        if value is None:
            return []
        if isinstance(value, list):
            flat: list[Any] = []
            for entry in value:
                if isinstance(entry, list):
                    flat.extend(e for e in entry if isinstance(e, dict))
                elif isinstance(entry, dict):
                    flat.append(entry)
            return flat
        return value

    @classmethod
    def from_source(cls, source: dict) -> ProcessoCapa:
        """Build a capa from an Elasticsearch hit ``_source`` dict."""
        return cls.model_validate(source)

    @property
    def cnj(self) -> str:
        """Normalized 20-digit CNJ (or the raw value when non-standard)."""
        return normalizar_cnj(self.numero_processo) or self.numero_processo

    def dedup_key(self) -> tuple[str, str, int | str | None]:
        """Natural key: (numeroProcesso, grau, orgaoJulgador.codigo or nome).

        Falls back to a namespaced ``nome`` when ``codigo`` is absent (not
        every tribunal populates it), so two distinct órgãos both missing
        ``codigo`` don't collapse onto the same key (see dedup.py).
        """
        codigo = self.orgao_julgador.codigo
        org = codigo if codigo is not None else f"nome:{self.orgao_julgador.nome or ''}"
        return (self.cnj, self.grau, org)

    def assuntos_str(self) -> str:
        """Distinct assunto names joined with '; ' (order preserved)."""
        seen: set[str] = set()
        nomes: list[str] = []
        for assunto in self.assuntos:
            if assunto.nome and assunto.nome not in seen:
                seen.add(assunto.nome)
                nomes.append(assunto.nome)
        return "; ".join(nomes)

    def capa_row(self, *, tribunal: str, consultado_em: str) -> dict:
        """Flatten the capa into a parquet row (see archive.CAPA_SCHEMA)."""
        return {
            "numero_processo": self.cnj,
            "tribunal": self.tribunal or tribunal.upper(),
            "grau": self.grau,
            "orgao_julgador_codigo": self.orgao_julgador.codigo,
            "orgao_julgador": self.orgao_julgador.nome,
            "classe_codigo": self.classe.codigo,
            "classe_nome": self.classe.nome,
            "assuntos": self.assuntos_str(),
            "sistema": self.sistema.nome,
            "formato": self.formato.nome,
            "nivel_sigilo": self.nivel_sigilo,
            "data_ajuizamento": normalizar_data14(self.data_ajuizamento),
            "ultima_atualizacao": self.data_hora_ultima_atualizacao,
            "n_movimentos": len(self.movimentos),
            "consultado_em": consultado_em,
        }

    def movimento_rows(self, *, tribunal: str) -> list[dict]:
        """Flatten the movimento line into parquet rows (MOVIMENTOS_SCHEMA)."""
        return [
            {
                "numero_processo": self.cnj,
                "tribunal": self.tribunal or tribunal.upper(),
                "grau": self.grau,
                "orgao_julgador_codigo": self.orgao_julgador.codigo,
                "codigo": mov.codigo,
                "nome": mov.nome,
                "data_hora": mov.data_hora,
                "complementos": mov.complementos_str(),
            }
            for mov in self.movimentos
        ]
