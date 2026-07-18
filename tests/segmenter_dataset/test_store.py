from __future__ import annotations

from pathlib import Path

import pytest
from conftest import make_annotation, make_document

from segmenter_dataset.store import ImmutabilityError, SegmenterDatasetStore


def test_write_and_read_document_round_trips(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    document = make_document()
    store.write_document(document)
    reloaded = store.read_document(document.document_id)
    assert reloaded == document


def test_write_document_twice_same_content_is_noop(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    document = make_document()
    store.write_document(document)
    store.write_document(document)  # should not raise
    assert len(store.list_documents()) == 1


def test_write_document_same_id_different_content_raises(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    document = make_document()
    store.write_document(document)

    # Force a collision: same document_id, different text, bypassing the
    # normal content-addressing path to simulate a hash-collision bug.
    forged = document.model_copy(update={"text": "different text entirely"})
    with pytest.raises(ImmutabilityError):
        store.write_document(forged)


def test_list_annotations_filters_by_document(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    doc_a = make_document(source_uri="u1")
    doc_b = make_document(source_uri="u2")
    store.write_document(doc_a)
    store.write_document(doc_b)
    store.write_annotation(make_annotation(doc_a))
    store.write_annotation(make_annotation(doc_b))

    assert len(store.list_annotations()) == 2
    assert len(store.list_annotations(document_id=doc_a.document_id)) == 1


def test_write_release_manifest_refuses_overwrite(tmp_path: Path) -> None:
    from segmenter_dataset.schemas import AnnotationQuality, ReleaseManifest

    store = SegmenterDatasetStore(tmp_path)
    manifest = ReleaseManifest(
        release_id="segmenter-silver-v8.1",
        ontology_version="segmenter-ontology-v8.0.0",
        guideline_version="g1",
        source_commit="a" * 40,
        dependency_lock_hash="b" * 64,
        split_hashes={"train": "t", "validation": "v", "test": "s"},
        document_resolutions={"train": {}, "validation": {}, "test": {}},
        annotation_quality=AnnotationQuality(),
        created_at="2026-01-01T00:00:00Z",
    )
    store.write_release_manifest(manifest)
    with pytest.raises(ImmutabilityError):
        store.write_release_manifest(manifest)
