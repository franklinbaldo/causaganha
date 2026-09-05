"""Regression tests for declared OKF scalar types in ProcessoConsultar (#1105)."""

from types import UnionType

from causaganha_mcp._generated.domain_models import (
    DjenResumoConcept,
    FonteCoberturaConcept,
    JurisDecisaoConcept,
    ProcessoConsultarProjection,
)


def _non_none_member(annotation: object) -> object:
    """Unwrap `X | None` to `X`; return `annotation` unchanged if it isn't a union."""
    if isinstance(annotation, UnionType):
        (member,) = (arg for arg in annotation.__args__ if arg is not type(None))
        return member
    return annotation


def test_declared_schema_types_drive_generated_projection() -> None:
    """Identifiers stay strings while semantic booleans/counts keep real types.

    `n_publicacoes`/`n_documentos` are legitimately nullable (#1105: a source can be
    present with the count not yet known), so the declared-type check unwraps
    `int | None` before comparing — the point of this test is the scalar kind
    (`int`, not the `infer_types` bug's misread), not whether it is also `Optional`.
    """
    assert ProcessoConsultarProjection.model_fields["nr_processo"].annotation is str
    assert ProcessoConsultarProjection.model_fields["encontrado"].annotation is bool
    assert ProcessoConsultarProjection.model_fields["documentos_truncados"].annotation is bool
    assert _non_none_member(DjenResumoConcept.model_fields["n_publicacoes"].annotation) is int
    assert _non_none_member(JurisDecisaoConcept.model_fields["n_documentos"].annotation) is int
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
