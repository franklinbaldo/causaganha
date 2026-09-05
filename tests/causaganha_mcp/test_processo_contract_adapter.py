"""Tests for the generated-contract adapter used by ``processo_consultar``."""

from __future__ import annotations

from causaganha.processos.models import (
    DatajudCapa,
    DjenResumo,
    DocumentoProcesso,
    FonteCobertura,
    JurisDecisao,
    ProcessoConsultaResult,
    StjAcordao,
)
from causaganha_mcp.processo_contract import serialize_shared_core


CNJ = "00000010220248220001"
CNJ_MASCARA = "0000001-02.2024.8.22.0001"


def test_shared_core_is_validated_then_exposed_in_public_vocabulary() -> None:
    result = ProcessoConsultaResult(
        encontrado=True,
        nr_processo=CNJ,
        nr_processo_mascara=CNJ_MASCARA,
        fontes_presentes=["djen", "juris", "stj", "datajud"],
        cobertura_dataset=[FonteCobertura(fonte="djen", status="loaded_remote", registros=10)],
        djen=DjenResumo(
            primeira_publicacao="2024-03-01",
            ultima_publicacao="2024-03-05",
            n_publicacoes=2,
            tribunais=["TJRO"],
        ),
        juris=JurisDecisao(
            n_documentos=1,
            tipos=["ACÓRDÃO"],
            data_julgamento=None,
            orgao=None,
            relator=None,
            classe=None,
            url=None,
        ),
        stj=StjAcordao(
            id="source-stj-1",
            classe="REsp",
            relator=None,
            tema=None,
            tese=None,
            ementa=None,
            data_decisao=None,
            data_publicacao=None,
        ),
        datajud=DatajudCapa(
            classe_oficial=None,
            assuntos=None,
            orgao_julgador=None,
            grau=None,
            data_ajuizamento=None,
            ultima_atualizacao=None,
        ),
        documentos=[
            DocumentoProcesso(
                fonte="stj",
                id_documento="source-stj-1",
                tipo=None,
                data=None,
                url=None,
                resumo=None,
            )
        ],
        dataset_gerado_em=None,
        avisos=["freshness desconhecida"],
    )

    payload = serialize_shared_core(result)

    assert payload["cnj"] == CNJ
    assert payload["cnj_formatado"] == CNJ_MASCARA
    assert "nr_processo" not in payload
    assert "type" not in payload
    assert "djen_id" not in payload
    assert payload["stj"]["id"] == "source-stj-1"
    assert payload["juris"]["relator"] is None
    assert payload["documentos"][0]["id_documento"] == "source-stj-1"
    assert payload["dataset_gerado_em"] is None


def test_shared_core_accepts_stj_without_class_or_source_identifier() -> None:
    result = ProcessoConsultaResult(
        encontrado=True,
        nr_processo=CNJ,
        nr_processo_mascara=CNJ_MASCARA,
        fontes_presentes=["stj"],
        stj=StjAcordao(
            id=None,
            classe=None,
            relator=None,
            tema=None,
            tese=None,
            ementa=None,
            data_decisao=None,
            data_publicacao=None,
        ),
    )

    payload = serialize_shared_core(result)

    assert payload["stj"] is not None
    assert payload["stj"]["id"] is None
    assert payload["stj"]["classe"] is None
