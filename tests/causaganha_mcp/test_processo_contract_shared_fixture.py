"""Cross-runtime contract fixture for the processo dossier (#1105)."""

from __future__ import annotations

import json
from pathlib import Path

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

FIXTURE = Path(__file__).parents[1] / "fixtures" / "processo_consultar_shared_core.json"


def _load_result() -> tuple[ProcessoConsultaResult, dict[str, object]]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw = fixture["domain_input"]
    result = ProcessoConsultaResult(
        encontrado=raw["encontrado"],
        nr_processo=raw["nr_processo"],
        nr_processo_mascara=raw["nr_processo_mascara"],
        fontes_presentes=raw["fontes_presentes"],
        cobertura_dataset=[FonteCobertura(**item) for item in raw["cobertura_dataset"]],
        djen=DjenResumo(**raw["djen"]) if raw["djen"] else None,
        juris=JurisDecisao(**raw["juris"]) if raw["juris"] else None,
        stj=StjAcordao(**raw["stj"]) if raw["stj"] else None,
        datajud=DatajudCapa(**raw["datajud"]) if raw["datajud"] else None,
        documentos=[DocumentoProcesso(**item) for item in raw["documentos"]],
        documentos_truncados=raw["documentos_truncados"],
        dataset_gerado_em=raw["dataset_gerado_em"],
        avisos=raw["avisos"],
    )
    return result, fixture["expected_shared"]


def test_mcp_serializer_matches_shared_fixture() -> None:
    result, expected = _load_result()
    payload = serialize_shared_core(result)

    comparable = {key: payload[key] for key in expected}
    assert comparable == expected
    assert payload["documentos"] == []
    assert payload["documentos_truncados"] is False
