"""Contract tests for the OKF-generated Pydantic domain models (#1105 slice 2).

`src/causaganha_mcp/_generated/domain_models.py` is produced mechanically by
`scripts/generate_okf_domain_models.py` from the `knowledge/` TypeContract
bundle — never edited by hand. These tests:

- catch drift between the checked-in generated file and what the current
  bundle would produce today (the same check CI runs before merge);
- prove `ProcessoConsultarProjection` actually validates realistic dossiê
  shapes end-to-end: full coverage, partial coverage (a source genuinely
  absent, not just empty), and a required field missing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from generate_okf_domain_models import _OUTPUT_PATH, render  # noqa: E402

from causaganha_mcp._generated.domain_models import (  # noqa: E402
    DatajudCapaConcept,
    DjenResumoConcept,
    DocumentoProcessoConcept,
    FonteCoberturaConcept,
    JurisDecisaoConcept,
    ProcessoConsultarProjection,
    StjAcordaoConcept,
)


def test_generated_domain_models_file_matches_current_knowledge_bundle() -> None:
    """The checked-in generated file must be exactly what `knowledge/` produces today.

    Fails the same way CI's drift gate does when someone edits the bundle
    (or the generated file itself) without rerunning the generator.
    """
    assert _OUTPUT_PATH.read_text(encoding="utf-8") == render()


def _fonte_cobertura(fonte: str, status: str, registros: str) -> dict[str, str]:
    return {
        "type": "FonteCobertura",
        "id": f"cobertura-{fonte}",
        "processo_nr": "01316736220028220001",
        "fonte": fonte,
        "status": status,
        "registros": registros,
    }


def test_processo_consultar_projection_validates_full_coverage_fixture() -> None:
    """A CNJ present in all four sources, with documents, validates as one shape."""
    fixture = {
        "type": "Processo",
        "nr_processo": "01316736220028220001",
        "nr_processo_mascara": "0131673-62.2002.8.22.0001",
        "encontrado": "true",
        "fontes_presentes": ["djen", "juris", "stj", "datajud"],
        "djen_id": "djen-1",
        "juris_id": "juris-1",
        "stj_id": "stj-1",
        "datajud_id": "datajud-1",
        "documentos_truncados": "false",
        "dataset_gerado_em": "2026-09-03T15:54:21+00:00",
        "avisos": [],
        "djen": {
            "type": "DjenResumo",
            "id": "djen-1",
            "primeira_publicacao": "2002-05-01",
            "ultima_publicacao": "2010-03-12",
            "n_publicacoes": "7",
            "tribunais": ["TJRO"],
        },
        "juris": {
            "type": "JurisDecisao",
            "id": "juris-1",
            "n_documentos": "2",
            "tipos": ["acordao"],
            "data_julgamento": "2009-11-04",
            "orgao": "1ª Câmara Cível",
            "relator": "Des. Fulano",
            "classe": "Apelação",
            "url": "https://tjro.jus.br/juris/juris-1",
        },
        "stj": {
            "type": "StjAcordao",
            "id": "stj-1",
            "classe": "REsp",
            "relator": "Min. Sicrana",
            "tema": "123",
            "tese": "Tese de exemplo.",
            "ementa": "Ementa de exemplo.",
            "data_decisao": "2011-02-01",
            "data_publicacao": "2011-02-15",
        },
        "datajud": {
            "type": "DatajudCapa",
            "id": "datajud-1",
            "classe_oficial": "Apelação Cível",
            "assuntos": "Indenização por Dano Moral",
            "orgao_julgador": "1ª Câmara Cível",
            "grau": "G2",
            "data_ajuizamento": "2002-04-20",
            "ultima_atualizacao": "2011-03-01T00:00:00+00:00",
        },
        "cobertura_dataset": [
            _fonte_cobertura("djen", "loaded_remote", "5539302"),
            _fonte_cobertura("juris", "loaded_remote", "1221386"),
            _fonte_cobertura("stj", "loaded_remote", "0"),
            _fonte_cobertura("datajud", "loaded_remote", "27"),
        ],
        "documentos": [
            {
                "type": "DocumentoProcesso",
                "fonte": "juris",
                "id_documento": "juris-1",
                "processo_nr": "01316736220028220001",
                "tipo": "acordao",
                "data": "2009-11-04",
                "url": "https://tjro.jus.br/juris/juris-1",
                "resumo": "Resumo truncado da decisão.",
            }
        ],
    }

    projection = ProcessoConsultarProjection.model_validate(fixture)

    assert projection.nr_processo == "01316736220028220001"
    assert isinstance(projection.djen, DjenResumoConcept)
    assert isinstance(projection.juris, JurisDecisaoConcept)
    assert isinstance(projection.stj, StjAcordaoConcept)
    assert isinstance(projection.datajud, DatajudCapaConcept)
    assert all(isinstance(c, FonteCoberturaConcept) for c in projection.cobertura_dataset)
    assert all(isinstance(d, DocumentoProcessoConcept) for d in projection.documentos)


def test_processo_consultar_projection_distinguishes_absent_source_from_empty_list() -> None:
    """A source genuinely absent from every fonte must validate as `None`, not an error.

    Only DJEN and JURIS have a record for this CNJ; STJ and DataJud are
    `None` rather than empty placeholder objects — the same "ausência de
    fonte" contract `ProcessoConsultarResult` (the hand-written MCP model)
    already honors.
    """
    fixture = {
        "type": "Processo",
        "nr_processo": "01316736220028220001",
        "nr_processo_mascara": "0131673-62.2002.8.22.0001",
        "encontrado": "true",
        "fontes_presentes": ["djen", "juris"],
        "djen_id": "djen-1",
        "juris_id": "juris-1",
        "stj_id": "",
        "datajud_id": "",
        "documentos_truncados": "false",
        "dataset_gerado_em": "2026-09-03T15:54:21+00:00",
        "avisos": [],
        "djen": {
            "type": "DjenResumo",
            "id": "djen-1",
            "primeira_publicacao": "2002-05-01",
            "ultima_publicacao": "2010-03-12",
            "n_publicacoes": "7",
            "tribunais": ["TJRO"],
        },
        "juris": {
            "type": "JurisDecisao",
            "id": "juris-1",
            "n_documentos": "2",
            "tipos": ["acordao"],
            "data_julgamento": "2009-11-04",
            "orgao": "1ª Câmara Cível",
            "relator": "Des. Fulano",
            "classe": "Apelação",
            "url": "https://tjro.jus.br/juris/juris-1",
        },
        "stj": None,
        "datajud": None,
        "cobertura_dataset": [
            _fonte_cobertura("djen", "loaded_remote", "5539302"),
            _fonte_cobertura("juris", "loaded_remote", "1221386"),
            _fonte_cobertura(
                "stj", "loaded_remote_zero_cnj_join", "0"
            ),  # #1045: loaded, joined nothing
            _fonte_cobertura("datajud", "unavailable", "0"),
        ],
        "documentos": [],
    }

    projection = ProcessoConsultarProjection.model_validate(fixture)

    assert projection.stj is None
    assert projection.datajud is None
    assert projection.documentos == []


def test_processo_consultar_projection_requires_nr_processo() -> None:
    """The identifier field is required — an incomplete payload must fail loudly."""
    fixture = {
        "type": "Processo",
        "nr_processo_mascara": "0131673-62.2002.8.22.0001",
        "encontrado": "false",
        "fontes_presentes": [],
        "djen_id": "",
        "juris_id": "",
        "stj_id": "",
        "datajud_id": "",
        "documentos_truncados": "false",
        "dataset_gerado_em": "2026-09-03T15:54:21+00:00",
        "avisos": [],
        "djen": None,
        "juris": None,
        "stj": None,
        "datajud": None,
        "cobertura_dataset": [],
        "documentos": [],
    }

    with pytest.raises(ValidationError, match="nr_processo"):
        ProcessoConsultarProjection.model_validate(fixture)


def test_generated_module_leaves_identifier_field_a_plain_string() -> None:
    """Regression guard for the upstream `infer_types=True` bug this generator avoids.

    okf-parser 0.45.6's `export_pydantic_source(..., infer_types=True)` infers
    `nr_processo`'s Python type from the bundle's example *value* rather than
    the relational schema's declared `VARCHAR`, producing `nr_processo: int`
    — which would silently drop a real CNJ's leading zero on validation
    (`int("0131673...")` discards the leading digit). Generating without
    `infer_types` keeps every scalar a plain `str`, so this can't happen; if
    a future okf-parser version changes the untyped default, this test (not
    a production CNJ lookup) is where that surfaces.
    """
    annotation = ProcessoConsultarProjection.model_fields["nr_processo"].annotation
    assert annotation is str
