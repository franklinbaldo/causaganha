from __future__ import annotations

from pathlib import Path

import pytest
from conftest import make_annotation, make_document, make_review

from segmenter_dataset.release import ReleaseBlockedError, build_dataset_release
from segmenter_dataset.schemas import Label
from segmenter_dataset.splits import (
    SplitAssignment,
    build_groups,
    create_split_manifest,
)
from segmenter_dataset.store import ImmutabilityError, SegmenterDatasetStore


ONTOLOGY = {"cabecalho_inicio", "cabecalho_fim"}
PAIR_LABELS = [
    Label(start=0, end=5, category="cabecalho_inicio"),
    Label(start=10, end=15, category="cabecalho_fim"),
]
SOURCE_COMMIT = "a" * 40
LOCK_HASH = "b" * 64


def _text_for(role: str, index: int) -> str:
    return f"0123{role}{index:03d}89ABCDEFGHIJ"


def _seed_release(
    store: SegmenterDatasetStore,
    *,
    n_train: int,
    n_val: int,
    n_test: int,
    same_eval_run: bool = False,
):
    train_ids: set[str] = set()
    val_ids: set[str] = set()
    test_ids: set[str] = set()

    for index in range(n_train):
        document = make_document(text=_text_for("train", index), source_uri=f"train-{index}")
        store.write_document(document)
        store.write_annotation(
            make_annotation(
                document,
                labels=PAIR_LABELS,
                covered_categories=tuple(sorted(ONTOLOGY)),
            )
        )
        train_ids.add(document.document_id)

    for role, count, ids in (("val", n_val, val_ids), ("test", n_test, test_ids)):
        for index in range(count):
            document = make_document(text=_text_for(role, index), source_uri=f"{role}-{index}")
            store.write_document(document)
            annotation_a = make_annotation(
                document,
                annotator_id="same-run" if same_eval_run else "run-a",
                model_family="same-family" if same_eval_run else "fam-a",
                completed_at="2026-01-01T00:00:00Z",
                labels=PAIR_LABELS,
                covered_categories=tuple(sorted(ONTOLOGY)),
            )
            annotation_b = make_annotation(
                document,
                annotator_id="same-run" if same_eval_run else "run-b",
                model_family="same-family" if same_eval_run else "fam-b",
                completed_at="2026-01-01T00:00:01Z",
                labels=PAIR_LABELS,
                covered_categories=tuple(sorted(ONTOLOGY)),
            )
            store.write_annotation(annotation_a)
            store.write_annotation(annotation_b)
            store.write_review(
                make_review(document, [annotation_a, annotation_b], final_labels=PAIR_LABELS)
            )
            ids.add(document.document_id)

    assignment = SplitAssignment(
        train_ids=frozenset(train_ids),
        val_ids=frozenset(val_ids),
        test_ids=frozenset(test_ids),
    )
    documents = store.list_documents()
    groups = build_groups(documents, near_duplicate_threshold=0.99)
    return create_split_manifest(
        assignment,
        groups,
        seed=7,
        train_ratio=0.70,
        val_ratio=0.15,
        near_duplicate_threshold=0.99,
    )


def _build(store: SegmenterDatasetStore, split_manifest, **overrides):
    kwargs = {
        "release_id": "segmenter-silver-v8.1",
        "ontology_version": "segmenter-ontology-v8.0.0",
        "guideline_version": "g1",
        "source_commit": SOURCE_COMMIT,
        "dependency_lock_hash": LOCK_HASH,
        "ci_provider": "github-actions",
        "ci_run_id": "12345",
        "ontology_categories": ONTOLOGY,
        "split_manifest": split_manifest,
        "iaa_seed": 1,
        "iaa_resamples": 100,
    }
    kwargs.update(overrides)
    return build_dataset_release(store, **kwargs)


def test_build_dataset_release_succeeds_and_writes_auditable_artifacts(
    tmp_path: Path,
) -> None:
    store = SegmenterDatasetStore(tmp_path)
    split_manifest = _seed_release(store, n_train=10, n_val=5, n_test=5)

    manifest = _build(store, split_manifest)

    assert manifest.counts == {"train": 10, "validation": 5, "test": 5}
    assert manifest.annotation_quality.val_iaa_span_f1 == 1.0
    release_dir = store.release_dir(manifest.release_id)
    assert (release_dir / "manifest.json").exists()
    assert (release_dir / "split_manifest.json").exists()
    assert (release_dir / "checksums.sha256").exists()
    assert manifest.iaa_seed == 1
    assert manifest.iaa_resamples == 100

    with pytest.raises(ImmutabilityError, match="already exists"):
        _build(store, split_manifest)


def test_zero_support_category_blocks_release(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    split_manifest = _seed_release(store, n_train=10, n_val=5, n_test=5)

    with pytest.raises(ReleaseBlockedError) as exc_info:
        _build(store, split_manifest, ontology_categories=ONTOLOGY | {"resultado"})

    gate_names = {gate.name for gate in exc_info.value.gate_results}
    assert "train_minimum_support_per_category" in gate_names
    assert "val_minimum_support_for_reported_metrics" in gate_names


def test_non_independent_eval_annotations_block_release(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    split_manifest = _seed_release(store, n_train=10, n_val=5, n_test=5, same_eval_run=True)

    with pytest.raises(ReleaseBlockedError) as exc_info:
        _build(store, split_manifest)

    assert "val_test_independently_adjudicated" in {
        gate.name for gate in exc_info.value.gate_results
    }


def test_review_with_missing_annotation_blocks_release(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    split_manifest = _seed_release(store, n_train=10, n_val=5, n_test=5)
    review = store.list_reviews()[0]
    review_path = store.reviews_dir / review.document_id / f"{review.review_id}.json"
    broken = review.model_copy(
        update={
            "input_annotation_ids": (
                review.input_annotation_ids[0],
                "ann_" + "f" * 32,
            )
        }
    )
    review_path.write_text(broken.model_dump_json(indent=2), encoding="utf-8")

    with pytest.raises(ReleaseBlockedError) as exc_info:
        _build(store, split_manifest)

    assert "no_unresolved_annotation_conflicts" in {
        gate.name for gate in exc_info.value.gate_results
    }


def test_release_recomputes_groups_and_rejects_manual_cross_split_near_duplicate(
    tmp_path: Path,
) -> None:
    store = SegmenterDatasetStore(tmp_path)
    split_manifest = _seed_release(store, n_train=10, n_val=5, n_test=5)
    train_id = split_manifest.train_ids[0]
    val_id = split_manifest.val_ids[0]
    train_doc = store.read_document(train_id)
    val_doc = store.read_document(val_id)
    val_path = store.documents_dir / f"{val_id}.json"
    near_duplicate = val_doc.model_copy(update={"text": train_doc.text + " "})
    val_path.write_text(near_duplicate.model_dump_json(indent=2), encoding="utf-8")

    with pytest.raises(ReleaseBlockedError) as exc_info:
        _build(store, split_manifest)

    assert "split_disjoint_by_group_id_hash" in {gate.name for gate in exc_info.value.gate_results}


def test_incomplete_build_provenance_blocks_release(tmp_path: Path) -> None:
    store = SegmenterDatasetStore(tmp_path)
    split_manifest = _seed_release(store, n_train=10, n_val=5, n_test=5)

    with pytest.raises(ReleaseBlockedError) as exc_info:
        _build(store, split_manifest, source_commit="abc123")

    assert "ci_reproducible_build" in {gate.name for gate in exc_info.value.gate_results}
