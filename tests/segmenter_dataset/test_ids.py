from __future__ import annotations

from segmenter_dataset.ids import annotation_id, document_id, review_id


def test_document_id_deterministic() -> None:
    kwargs = {"source_system": "tjro_juris", "source_uri": "u1", "source_hash": "h1"}
    assert document_id(**kwargs) == document_id(**kwargs)


def test_document_id_ignores_text_only_depends_on_source() -> None:
    kwargs = {"source_system": "tjro_juris", "source_uri": "u1", "source_hash": "h1"}
    a = document_id(**kwargs)
    b = document_id(**kwargs)
    assert a == b


def test_document_id_differs_for_different_source() -> None:
    a = document_id(source_system="tjro_juris", source_uri="u1", source_hash="h1")
    b = document_id(source_system="tjro_juris", source_uri="u2", source_hash="h1")
    assert a != b


def test_annotation_id_differs_for_different_labels() -> None:
    base = {
        "document_id": "doc_1",
        "annotator_id": "haiku",
        "completed_at": "2026-01-01T00:00:00Z",
    }
    a = annotation_id(labels=[{"start": 0, "end": 5, "category": "x"}], **base)
    b = annotation_id(labels=[{"start": 0, "end": 6, "category": "x"}], **base)
    assert a != b


def test_annotation_id_same_content_same_id() -> None:
    base = {
        "document_id": "doc_1",
        "annotator_id": "haiku",
        "completed_at": "2026-01-01T00:00:00Z",
        "labels": [{"start": 0, "end": 5, "category": "x"}],
    }
    assert annotation_id(**base) == annotation_id(**base)


def test_review_id_order_independent_on_input_annotation_ids() -> None:
    a = review_id(document_id="doc_1", input_annotation_ids=["ann_a", "ann_b"], approved_at="t")
    b = review_id(document_id="doc_1", input_annotation_ids=["ann_b", "ann_a"], approved_at="t")
    assert a == b
