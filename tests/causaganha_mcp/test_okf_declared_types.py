"""Regression tests for declared OKF scalar types in ProcessoConsultar (#1105)."""

from causaganha_mcp._generated.domain_models import (
    DjenResumoConcept,
    FonteCoberturaConcept,
    JurisDecisaoConcept,
    ProcessoConsultarProjection,
)


def test_declared_schema_types_drive_generated_projection() -> None:
    """Identifiers stay strings while semantic booleans/counts keep real types."""
    assert ProcessoConsultarProjection.model_fields["nr_processo"].annotation is str
    assert ProcessoConsultarProjection.model_fields["encontrado"].annotation is bool
    assert ProcessoConsultarProjection.model_fields["documentos_truncados"].annotation is bool
    assert DjenResumoConcept.model_fields["n_publicacoes"].annotation is int
    assert JurisDecisaoConcept.model_fields["n_documentos"].annotation is int
    assert FonteCoberturaConcept.model_fields["registros"].annotation is int


def test_declared_types_preserve_runtime_values() -> None:
    projection = ProcessoConsultarProjection.model_validate(
        {
            "type": "Processo",
            "nr_processo": "01316736220028220001",
            "nr_processo_mascara": "0131673-62.2002.8.22.0001",
            "encontrado": True,
            "fontes_presentes": [],
            "djen_id": "",
            "juris_id": "",
            "stj_id": "",
            "datajud_id": "",
            "documentos_truncados": False,
            "dataset_gerado_em": "2026-09-04T00:00:00+00:00",
            "avisos": [],
            "djen": None,
            "juris": None,
            "stj": None,
            "datajud": None,
            "cobertura_dataset": [],
            "documentos": [],
        }
    )

    assert projection.nr_processo == "01316736220028220001"
    assert projection.encontrado is True
    assert projection.documentos_truncados is False
