"""Adapter between the process domain result and the generated OKF product core.

The generated ``ProcessoConsultarProjection`` still carries relational/OKF
identity metadata that is intentionally not part of the public MCP envelope.
This module keeps that translation in one place: domain data is first
validated by the generated contract and only then projected to the public
product vocabulary used by ``processo_consultar``.
"""

from __future__ import annotations

from typing import Any

from causaganha.processos.models import ProcessoConsultaResult
from causaganha_mcp._generated.domain_models import ProcessoConsultarProjection


def _concept_id(cnj: str, source: str) -> str:
    """Return a stable internal identity for a related OKF concept.

    These identifiers exist only to satisfy relational identity inside the
    generated contract. They are never exposed as source identifiers by the
    MCP surface.
    """
    return f"{source}:{cnj}"


def _projection_payload(r: ProcessoConsultaResult) -> dict[str, Any]:
    cnj = r.nr_processo
    djen_id = _concept_id(cnj, "djen") if r.djen is not None else None
    juris_id = _concept_id(cnj, "juris") if r.juris is not None else None
    stj_id = _concept_id(cnj, "stj") if r.stj is not None else None
    datajud_id = _concept_id(cnj, "datajud") if r.datajud is not None else None

    return {
        "type": "Processo",
        "nr_processo": cnj,
        "nr_processo_mascara": r.nr_processo_mascara,
        "encontrado": r.encontrado,
        "fontes_presentes": r.fontes_presentes,
        "djen_id": djen_id,
        "juris_id": juris_id,
        "stj_id": stj_id,
        "datajud_id": datajud_id,
        "documentos_truncados": r.documentos_truncados,
        "dataset_gerado_em": r.dataset_gerado_em,
        "avisos": r.avisos,
        "djen": (
            {
                "type": "DjenResumo",
                "id": djen_id,
                "primeira_publicacao": r.djen.primeira_publicacao,
                "ultima_publicacao": r.djen.ultima_publicacao,
                "n_publicacoes": r.djen.n_publicacoes,
                "tribunais": r.djen.tribunais,
            }
            if r.djen is not None
            else None
        ),
        "juris": (
            {
                "type": "JurisDecisao",
                "id": juris_id,
                "n_documentos": r.juris.n_documentos,
                "tipos": r.juris.tipos,
                "data_julgamento": r.juris.data_julgamento,
                "orgao": r.juris.orgao,
                "relator": r.juris.relator,
                "classe": r.juris.classe,
                "url": r.juris.url,
            }
            if r.juris is not None
            else None
        ),
        "stj": (
            {
                "type": "StjAcordao",
                "id": stj_id,
                "classe": r.stj.classe,
                "relator": r.stj.relator,
                "tema": r.stj.tema,
                "tese": r.stj.tese,
                "ementa": r.stj.ementa,
                "data_decisao": r.stj.data_decisao,
                "data_publicacao": r.stj.data_publicacao,
            }
            if r.stj is not None
            else None
        ),
        "datajud": (
            {
                "type": "DatajudCapa",
                "id": datajud_id,
                "classe_oficial": r.datajud.classe_oficial,
                "assuntos": r.datajud.assuntos,
                "orgao_julgador": r.datajud.orgao_julgador,
                "grau": r.datajud.grau,
                "data_ajuizamento": r.datajud.data_ajuizamento,
                "ultima_atualizacao": r.datajud.ultima_atualizacao,
            }
            if r.datajud is not None
            else None
        ),
        "cobertura_dataset": [
            {
                "type": "FonteCobertura",
                "id": _concept_id(cnj, f"cobertura:{c.fonte}"),
                "processo_nr": cnj,
                "fonte": c.fonte,
                "status": c.status,
                "registros": c.registros,
            }
            for c in r.cobertura_dataset
        ],
        "documentos": [
            {
                "type": "DocumentoProcesso",
                "processo_nr": cnj,
                "fonte": d.fonte,
                "id_documento": d.id_documento,
                "tipo": d.tipo,
                "data": d.data,
                "url": d.url,
                "resumo": d.resumo,
            }
            for d in r.documentos
        ],
    }


def serialize_shared_core(r: ProcessoConsultaResult) -> dict[str, Any]:
    """Validate the shared dossier core and return its public product shape.

    Surface-only fields such as ``consultado_em``, ``next_actions`` and web
    links are deliberately absent. The public STJ ``id`` remains the source
    identifier from the domain model; the generated relation uses a separate
    internal concept identity so a missing source identifier never becomes a
    fabricated public value.
    """
    core = ProcessoConsultarProjection.model_validate(_projection_payload(r))

    return {
        "encontrado": core.encontrado,
        "cnj": core.nr_processo,
        "cnj_formatado": core.nr_processo_mascara,
        "fontes_presentes": core.fontes_presentes,
        "cobertura_dataset": [
            {"fonte": c.fonte, "status": c.status, "registros": c.registros}
            for c in core.cobertura_dataset
        ],
        "djen": (
            {
                "primeira_publicacao": core.djen.primeira_publicacao,
                "ultima_publicacao": core.djen.ultima_publicacao,
                "n_publicacoes": core.djen.n_publicacoes,
                "tribunais": core.djen.tribunais,
            }
            if core.djen is not None
            else None
        ),
        "juris": (
            {
                "n_documentos": core.juris.n_documentos,
                "tipos": core.juris.tipos,
                "data_julgamento": core.juris.data_julgamento,
                "orgao": core.juris.orgao,
                "relator": core.juris.relator,
                "classe": core.juris.classe,
                "url": core.juris.url,
            }
            if core.juris is not None
            else None
        ),
        "stj": (
            {
                "id": r.stj.id,
                "classe": core.stj.classe,
                "relator": core.stj.relator,
                "tema": core.stj.tema,
                "tese": core.stj.tese,
                "ementa": core.stj.ementa,
                "data_decisao": core.stj.data_decisao,
                "data_publicacao": core.stj.data_publicacao,
            }
            if core.stj is not None and r.stj is not None
            else None
        ),
        "datajud": (
            {
                "classe_oficial": core.datajud.classe_oficial,
                "assuntos": core.datajud.assuntos,
                "orgao_julgador": core.datajud.orgao_julgador,
                "grau": core.datajud.grau,
                "data_ajuizamento": core.datajud.data_ajuizamento,
                "ultima_atualizacao": core.datajud.ultima_atualizacao,
            }
            if core.datajud is not None
            else None
        ),
        "documentos": [
            {
                "fonte": d.fonte,
                "id_documento": d.id_documento,
                "tipo": d.tipo,
                "data": d.data,
                "url": d.url,
                "resumo": d.resumo,
            }
            for d in core.documentos
        ],
        "documentos_truncados": core.documentos_truncados,
        "dataset_gerado_em": core.dataset_gerado_em,
        "avisos": core.avisos,
    }
