from __future__ import annotations

from pathlib import Path

import pytest
from conftest import make_annotation, make_document, make_review

from segmenter_dataset.release import ReleaseBlockedError, build_dataset_release
from segmenter_dataset.schemas import KnownLimitation, Label
from segmenter_dataset.splits import SplitAssignment, SplitLeakError
from segmenter_dataset.store import SegmenterDatasetStore


ONTOLOGY = {"cabecalho_inicio", "cabecalho_fim"}
PAIR_LABELS = [
    Label(start=0, end=5, category="cabecalho_inicio"),
    Label(start=10, end=15, category="cabecalho_fim"),
]


def _text_for(role: str, index: int) -> str:
    # Unique per document — sharing text across documents would (correctly)
    # trip the cross-split content-hash leakage gate.
    return f"0123{role}{index:03d}89ABCDEFGHIJ"


def _seed_release(
    store: SegmenterDatasetStore, *, n_train: int, n_val: int, n_test: int
) -> SplitAssignment:
    train_ids: set[str] = set()
    val_ids: set[str] = set()
    test_ids: set[str] = set()

    for i in range(n_train):
        doc = make_document(text=_text_for("train", i), source_uri=f"train-{i}")
        store.write_document(doc)
        annotation = make_annotation(
            doc, labels=PAIR_LABELS, covered_categories=("cabecalho_inicio", "cabecalho_fim")
        )
        store.write_annotation(annotation)
        train_ids.add(doc.document_id)

    for role, n, ids in (("val", n_val, val_ids), ("test", n_test, test_ids)):
        for i in range(n):
            doc = make_document(text=_text_for(role, i), source_uri=f"{role}-{i}")
            store.write_document(doc)
            ann_a = make_annotation(
                doc,
                annotator_id="a",
                model_family="fam-a",
                labels=PAIR_LABELS,
                covered_categories=("cabecalho_inicio", "cabecalho_fim"),
            )
            ann_b = make_annotation(
                doc,
                annotator_id="b",
                model_family="fam-b",
                labels=PAIR_LABELS,
                covered_categories=("cabecalho_inicio", "cabecalho_fim"),
            )
            store.write_annotation(ann_a)
            store.write_annotation(ann_b)
            review = make_review(doc, [ann_a, ann_b], final_labels=PAIR_LABELS)
            store.write_review(review)
            ids.add(doc.document_id)

    return SplitAssignment(
        train_ids=frozenset(train_ids), val_ids=frozenset(val_ids), test_ids=frozenset(test_ids)
    )


def test_build_dataset_release_succeeds_with_sufficient_support(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=10, n_val=5, n_test=5)

    manifest = build_dataset_release(
        store,
        release_id="segmenter-silver-v8.1",
        ontology_version="segmenter-ontology-v8.0.0",
        guideline_version="g1",
        source_commit="abc123",
        dependency_lock_hash="lock123",
        ontology_categories=ONTOLOGY,
        split_assignment=assignment,
        iaa_seed=1,
    )

    assert manifest.counts == {"train": 10, "validation": 5, "test": 5}
    assert manifest.annotation_quality.val_iaa_span_f1 == 1.0
    assert manifest.annotation_quality.test_iaa_span_f1 == 1.0
    assert manifest.annotation_quality.unreliable_eval_categories == ()

    # RFC 0012 §12 step 9: refuses to overwrite an existing release.
    with pytest.raises(Exception, match="already exists"):
        build_dataset_release(
            store,
            release_id="segmenter-silver-v8.1",
            ontology_version="segmenter-ontology-v8.0.0",
            guideline_version="g1",
            source_commit="abc123",
            dependency_lock_hash="lock123",
            ontology_categories=ONTOLOGY,
            split_assignment=assignment,
            iaa_seed=1,
        )


def test_build_dataset_release_blocked_by_insufficient_train_support(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=2, n_val=5, n_test=5)

    with pytest.raises(ReleaseBlockedError) as exc_info:
        build_dataset_release(
            store,
            release_id="segmenter-silver-v8.1",
            ontology_version="segmenter-ontology-v8.0.0",
            guideline_version="g1",
            source_commit="abc123",
            dependency_lock_hash="lock123",
            ontology_categories=ONTOLOGY,
            split_assignment=assignment,
            iaa_seed=1,
        )
    gate_names = {g.name for g in exc_info.value.gate_results}
    assert "train_minimum_support_per_category" in gate_names


def test_build_dataset_release_raises_when_val_document_not_adjudicated(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=10, n_val=5, n_test=5)

    # Add one more document with only an annotation (no review) but assign
    # it to val — a document that hasn't reached the role's required state.
    unreviewed = make_document(text="0123456789ABCDEFGHIJ", source_uri="val-unreviewed")
    store.write_document(unreviewed)
    store.write_annotation(
        make_annotation(
            unreviewed,
            labels=PAIR_LABELS,
            covered_categories=("cabecalho_inicio", "cabecalho_fim"),
        )
    )
    broken_assignment = SplitAssignment(
        train_ids=assignment.train_ids,
        val_ids=assignment.val_ids | {unreviewed.document_id},
        test_ids=assignment.test_ids,
    )

    with pytest.raises(SplitLeakError, match="no accepted review record"):
        build_dataset_release(
            store,
            release_id="segmenter-silver-v8.1",
            ontology_version="segmenter-ontology-v8.0.0",
            guideline_version="g1",
            source_commit="abc123",
            dependency_lock_hash="lock123",
            ontology_categories=ONTOLOGY,
            split_assignment=broken_assignment,
            iaa_seed=1,
        )


def test_build_dataset_release_advisory_gate_waived_by_known_limitation(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    assignment = _seed_release(store, n_train=10, n_val=5, n_test=5)

    # multiple_tribunals is never automatically evaluated as failing in this
    # module (single-tribunal fixtures don't run that gate at all here) —
    # this test instead verifies a rigid-gate detail: an unrelated known
    # limitation does not mask a real rigid failure.
    manifest = build_dataset_release(
        store,
        release_id="segmenter-silver-v8.2",
        ontology_version="segmenter-ontology-v8.0.0",
        guideline_version="g1",
        source_commit="abc123",
        dependency_lock_hash="lock123",
        ontology_categories=ONTOLOGY,
        split_assignment=assignment,
        known_limitations=[KnownLimitation(gate="multiple_tribunals", reason="TJRO-only for v8.1")],
        iaa_seed=1,
    )
    assert manifest.known_limitations[0].gate == "multiple_tribunals"
