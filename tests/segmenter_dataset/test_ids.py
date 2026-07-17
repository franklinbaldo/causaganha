from __future__ import annotations

from segmenter_dataset.ids import annotation_id, document_id, review_id


BASE_ANNOTATION = {
    "document_id": "doc_" + "1" * 32,
    "annotator_id": "haiku-run-1",
    "annotator_config": {
        "model_family": "haiku",
        "guideline_version": "g1",
        "seeded_with": "none",
    },
    "ontology_version": "segmenter-ontology-v8.0.0",
    "covered_categories": ["x"],
    "labels": [{"start": 0, "end": 5, "category": "x"}],
    "allowed_unmatched": {},
    "completed_at": "2026-01-01T00:00:00Z",
    "annotation_method": "independent_full_read",
}

BASE_REVIEW = {
    "document_id": "doc_" + "1" * 32,
    "input_annotation_ids": ["ann_" + "a" * 32, "ann_" + "b" * 32],
    "status": "accepted",
    "final_labels": [{"start": 0, "end": 5, "category": "x"}],
    "allowed_unmatched": {},
    "reviewers": ["r1", "r2"],
    "resolution": "agreement",
    "notes": [],
    "approved_at": "2026-01-02T00:00:00Z",
}


def test_document_id_deterministic() -> None:
    kwargs = {"source_system": "tjro_juris", "source_uri": "u1", "source_hash": "h1"}
    assert document_id(**kwargs) == document_id(**kwargs)


def test_document_id_differs_for_different_source() -> None:
    first = document_id(source_system="tjro_juris", source_uri="u1", source_hash="h1")
    second = document_id(source_system="tjro_juris", source_uri="u2", source_hash="h1")
    assert first != second


def test_annotation_id_changes_for_every_semantic_field() -> None:
    original = annotation_id(**BASE_ANNOTATION)
    changed = dict(BASE_ANNOTATION)
    changed["covered_categories"] = ["x", "y"]
    assert annotation_id(**changed) != original

    changed = dict(BASE_ANNOTATION)
    changed["annotator_config"] = {
        **BASE_ANNOTATION["annotator_config"],
        "guideline_version": "g2",
    }
    assert annotation_id(**changed) != original


def test_annotation_id_same_content_same_id() -> None:
    assert annotation_id(**BASE_ANNOTATION) == annotation_id(**BASE_ANNOTATION)


def test_review_id_order_independent_on_inputs_and_reviewers() -> None:
    first = review_id(**BASE_REVIEW)
    changed = dict(BASE_REVIEW)
    changed["input_annotation_ids"] = list(reversed(BASE_REVIEW["input_annotation_ids"]))
    changed["reviewers"] = list(reversed(BASE_REVIEW["reviewers"]))
    assert review_id(**changed) == first


def test_review_id_changes_when_final_labels_change() -> None:
    changed = dict(BASE_REVIEW)
    changed["final_labels"] = [{"start": 0, "end": 6, "category": "x"}]
    assert review_id(**changed) != review_id(**BASE_REVIEW)
