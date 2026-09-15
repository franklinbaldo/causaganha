"""Tests for scripts/adjudicate_segmenter_review.py (RFC 0012 §8/§9, issue #1050/#1051).

Builds a :class:`~segmenter_dataset.schemas.ReviewRecord` from a pair of
annotations plus a reviewer's own fully tagged resolution — the review's
independence requirement (RFC 0012 §5.3) is deliberately *not* re-checked
here: it already lives at persistence time in
``SegmenterDatasetStore.write_review`` (its ``NonIndependentReviewError``
guard), so this module's job is only to build a well-formed candidate and
let that existing guard be the actual enforcement point (see
``test_store_rejects_non_independent_pair_at_write_time`` below).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from conftest import make_annotation, make_document

from segmenter_dataset.schemas import Label
from segmenter_dataset.store import NonIndependentReviewError, SegmenterDatasetStore


def load_script(module_name: str, path: str) -> object:
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


_MODULE = load_script("adjudicate_segmenter_review", "scripts/adjudicate_segmenter_review.py")

_ONTOLOGY_CATEGORIES = {"cabecalho_inicio", "cabecalho_fim", "resultado"}


def test_diff_labels_partitions_matched_only_a_only_b() -> None:
    labels_a = [
        Label(start=0, end=9, category="cabecalho_inicio"),
        Label(start=10, end=20, category="resultado"),
    ]
    labels_b = [
        Label(start=0, end=9, category="cabecalho_inicio"),
        Label(start=10, end=25, category="resultado"),  # different end -> disagreement
    ]

    diff = _MODULE.diff_labels(labels_a, labels_b)

    assert diff.matched == (Label(start=0, end=9, category="cabecalho_inicio"),)
    assert diff.only_a == (Label(start=10, end=20, category="resultado"),)
    assert diff.only_b == (Label(start=10, end=25, category="resultado"),)


def test_build_review_happy_path_independent_pair() -> None:
    document = make_document(text="CABEÇALHO texto julgo procedente fim.")
    annotation_a = make_annotation(
        document,
        annotator_id="ann-a",
        model_family="family-a",
        labels=[
            Label(start=0, end=9, category="cabecalho_inicio"),
            Label(start=16, end=33, category="resultado"),
        ],
        covered_categories=("cabecalho_inicio", "resultado"),
    )
    annotation_b = make_annotation(
        document,
        annotator_id="ann-b",
        model_family="family-b",
        labels=[Label(start=0, end=9, category="cabecalho_inicio")],
        covered_categories=("cabecalho_inicio", "resultado"),
    )
    resolution_tagged = (
        "<cabecalho><inicio>CABEÇALHO</inicio> texto "
        "<resultado>julgo procedente</resultado> <fim>fim.</fim></cabecalho>"
    )

    review = _MODULE.build_review(
        document,
        annotation_a,
        annotation_b,
        resolution_tagged,
        reviewers=("segmenter_dataset_agent_review:v1",),
        resolution="adopted annotation_a's resultado span; both agreed on cabecalho",
        approved_at="2026-09-15T09:00:00Z",
        ontology_categories=_ONTOLOGY_CATEGORIES,
    )

    assert review.review_id.startswith("rev_")
    assert review.status == "accepted"
    assert review.input_annotation_ids == (annotation_a.annotation_id, annotation_b.annotation_id)
    assert {label.category for label in review.final_labels} == {
        "cabecalho_inicio",
        "cabecalho_fim",
        "resultado",
    }
    assert review.notes  # diff summary recorded


def test_build_review_drops_ref_normativa_before_validation() -> None:
    """A reviewer's resolution may carry ``ref_normativa`` spans copied from an input

    annotation (``ref_normativa`` is excluded from the trainable ontology, RFC 0012 §5
    decision 1). ``annotate_second_independent.py`` already drops it automatically before
    persisting an annotation; a resolution file built from one of those annotations'
    tagged text can still carry the tag verbatim, so ``build_review`` must apply the same
    drop instead of failing mechanical validation on a category the caller never intended
    to keep (found live in agent-run 2jz691: two of three resolutions this round needed a
    manual tag strip for exactly this).
    """
    document = make_document(text="julgo procedente nos termos do art. 5 fim.")
    annotation_a = make_annotation(document, annotator_id="ann-a", model_family="family-a")
    annotation_b = make_annotation(document, annotator_id="ann-b", model_family="family-b")
    resolution_tagged = (
        "<resultado>julgo procedente</resultado> nos termos do "
        "<ref_normativa>art. 5</ref_normativa> fim."
    )

    review = _MODULE.build_review(
        document,
        annotation_a,
        annotation_b,
        resolution_tagged,
        reviewers=("segmenter_dataset_agent_review:v1",),
        resolution="kept resultado only; ref_normativa is out of scope for v8",
        approved_at="2026-09-15T09:00:00Z",
        ontology_categories={"resultado"},
    )

    assert [label.category for label in review.final_labels] == ["resultado"]


def test_build_review_verbatim_mismatch_raises() -> None:
    document = make_document(text="CABEÇALHO texto fim.")
    annotation_a = make_annotation(document, annotator_id="ann-a", model_family="family-a")
    annotation_b = make_annotation(document, annotator_id="ann-b", model_family="family-b")
    wrong_resolution = "<cabecalho_inicio>CABEÇALHO</cabecalho_inicio> outro texto fim."

    with pytest.raises(_MODULE.VerbatimFidelityError):
        _MODULE.build_review(
            document,
            annotation_a,
            annotation_b,
            wrong_resolution,
            reviewers=("reviewer1",),
            resolution="n/a",
            approved_at="2026-09-15T09:00:00Z",
            ontology_categories=_ONTOLOGY_CATEGORIES,
        )


def test_build_review_mechanical_validation_failure_raises() -> None:
    document = make_document(text="julgo procedente e julgo improcedente.")
    annotation_a = make_annotation(document, annotator_id="ann-a", model_family="family-a")
    annotation_b = make_annotation(document, annotator_id="ann-b", model_family="family-b")
    resolution_tagged = (
        "<resultado>julgo procedente</resultado> e <resultado>julgo improcedente</resultado>."
    )

    with pytest.raises(_MODULE.MechanicalValidationError):
        _MODULE.build_review(
            document,
            annotation_a,
            annotation_b,
            resolution_tagged,
            reviewers=("reviewer1",),
            resolution="n/a",
            approved_at="2026-09-15T09:00:00Z",
            ontology_categories={"resultado"},
        )


def test_main_passes_allowed_unmatched_through_cli(tmp_path: Path) -> None:
    """The CLI must expose ``--allowed-unmatched`` like its sibling script does.

    Without it, a resolution with a genuinely unmatched pair (guideline-valid
    when no closing cue exists in the source) has no way to declare that
    reason, and ``build_review`` raises ``MechanicalValidationError`` even
    though the same resolution would be accepted with the reason attached.
    """
    store = SegmenterDatasetStore(tmp_path / "store")
    document = make_document(text="CABEÇALHO texto sem fechamento.")
    store.write_document(document)
    annotation_a = make_annotation(document, annotator_id="ann-a", model_family="family-a")
    annotation_b = make_annotation(document, annotator_id="ann-b", model_family="family-b")
    store.write_annotation(annotation_a)
    store.write_annotation(annotation_b)
    resolution_path = tmp_path / "resolution.txt"
    resolution_path.write_text(
        "<cabecalho><inicio>CABEÇALHO</inicio></cabecalho> texto sem fechamento.",
        encoding="utf-8",
    )
    label_space_path = tmp_path / "label_space.json"
    label_space_path.write_text(
        '{"span_class_names": ["cabecalho_inicio", "cabecalho_fim"]}', encoding="utf-8"
    )

    _MODULE.main(
        [
            "--data-root",
            str(tmp_path / "store"),
            "--document-id",
            document.document_id,
            "--annotation-a",
            annotation_a.annotation_id,
            "--annotation-b",
            annotation_b.annotation_id,
            "--resolution-file",
            str(resolution_path),
            "--reviewers",
            "reviewer1",
            "--resolution",
            "cabecalho sem cue de fechamento; unmatched declarado",
            "--approved-at",
            "2026-09-15T09:00:00Z",
            "--label-space",
            str(label_space_path),
            "--allowed-unmatched",
            '{"cabecalho": "sem cue de fechamento no documento"}',
        ]
    )

    [review] = store.list_reviews(document.document_id)
    assert review.allowed_unmatched == {"cabecalho": "sem cue de fechamento no documento"}


def test_store_rejects_non_independent_pair_at_write_time(tmp_path: Path) -> None:
    """``build_review`` itself doesn't re-check independence -- the store does.

    A pair seeded from one another (or same-family) should still fail, but
    at ``store.write_review``, via its existing ``NonIndependentReviewError``
    guard -- not silently succeed here.
    """
    store = SegmenterDatasetStore(tmp_path / "store")
    document = make_document(text="CABEÇALHO texto fim.")
    store.write_document(document)
    annotation_a = make_annotation(document, annotator_id="ann-a", model_family="family-a")
    annotation_b = make_annotation(
        document, annotator_id="ann-b", model_family="family-a"
    )  # same family -> not independent
    store.write_annotation(annotation_a)
    store.write_annotation(annotation_b)
    resolution_tagged = "<cabecalho><inicio>CABEÇALHO</inicio> texto <fim>fim.</fim></cabecalho>"

    review = _MODULE.build_review(
        document,
        annotation_a,
        annotation_b,
        resolution_tagged,
        reviewers=("reviewer1",),
        resolution="n/a",
        approved_at="2026-09-15T09:00:00Z",
        ontology_categories=_ONTOLOGY_CATEGORIES,
    )

    with pytest.raises(NonIndependentReviewError):
        store.write_review(review)
