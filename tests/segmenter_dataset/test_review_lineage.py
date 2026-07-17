from __future__ import annotations

from conftest import make_annotation, make_document, make_review

from segmenter_dataset.mechanical import validate_review_lineage


ONTOLOGY = {"cabecalho_inicio", "cabecalho_fim"}


def test_review_lineage_rejects_same_run_and_family() -> None:
    document = make_document()
    first = make_annotation(
        document,
        annotator_id="same-run",
        model_family="same-family",
        completed_at="2026-01-01T00:00:00Z",
        covered_categories=tuple(sorted(ONTOLOGY)),
    )
    second = make_annotation(
        document,
        annotator_id="same-run",
        model_family="same-family",
        completed_at="2026-01-01T00:00:01Z",
        covered_categories=tuple(sorted(ONTOLOGY)),
    )
    review = make_review(document, [first, second])

    problems = validate_review_lineage(
        review,
        {first.annotation_id: first, second.annotation_id: second},
        ontology_version="segmenter-ontology-v8.0.0",
        ontology_categories=ONTOLOGY,
    )

    assert any("independent execution" in problem for problem in problems)
