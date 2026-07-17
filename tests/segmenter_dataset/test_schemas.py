from __future__ import annotations

import pytest
from conftest import make_annotation, make_document, make_review
from pydantic import ValidationError

from segmenter_dataset.schemas import Label


def test_label_rejects_bad_offsets() -> None:
    with pytest.raises(ValidationError):
        Label(start=5, end=5, category="x")
    with pytest.raises(ValidationError):
        Label(start=6, end=5, category="x")


def test_annotation_rejects_label_outside_covered_categories() -> None:
    document = make_document()
    with pytest.raises(ValidationError, match="covered_categories"):
        make_annotation(
            document,
            labels=[Label(start=0, end=9, category="resultado")],
            covered_categories=("cabecalho_inicio",),
        )


def test_review_requires_two_inputs_when_accepted() -> None:
    document = make_document()
    annotation = make_annotation(document)
    with pytest.raises(ValidationError, match="at least two"):
        make_review(document, [annotation], status="accepted")


def test_review_accepts_two_inputs() -> None:
    document = make_document()
    a = make_annotation(document, annotator_id="a", model_family="fam-a")
    b = make_annotation(document, annotator_id="b", model_family="fam-b")
    review = make_review(document, [a, b])
    assert review.status == "accepted"
    assert len(review.input_annotation_ids) == 2
