"""Regression for the shared ProcessoConsultar semantic core when every source is absent."""

from causaganha_mcp._generated.domain_models import ProcessoConsultarProjection


def test_projection_accepts_valid_process_absent_from_all_sources() -> None:
    payload = {
        "type": "Processo",
        "nr_processo": "11111111111111111111",
        "nr_processo_mascara": "1111111-11.1111.1.11.1111",
        "encontrado": False,
        "fontes_presentes": [],
        "djen_id": None,
        "juris_id": None,
        "stj_id": None,
        "datajud_id": None,
        "documentos_truncados": False,
        "dataset_gerado_em": None,
        "avisos": ["relatorio_indisponivel"],
        "djen": None,
        "juris": None,
        "stj": None,
        "datajud": None,
        "cobertura_dataset": [],
        "documentos": [],
    }

    result = ProcessoConsultarProjection.model_validate(payload)

    assert result.encontrado is False
    assert result.dataset_gerado_em is None
    assert result.djen_id is None
    assert result.juris_id is None
    assert result.stj_id is None
    assert result.datajud_id is None
