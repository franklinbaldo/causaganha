from __future__ import annotations

import json
from pathlib import Path

from conftest import make_annotation, make_document, make_review

from segmenter_dataset.opf_export import (
    export_release_for_training,
    resolve_release_documents,
    to_opf_record,
    write_label_space,
)
from segmenter_dataset.release import build_dataset_release
from segmenter_dataset.schemas import KnownLimitation, Label
from segmenter_dataset.splits import (
    GroupingKeys,
    SplitAssignment,
    build_groups,
    create_split_manifest,
)
from segmenter_dataset.store import SegmenterDatasetStore


ONTOLOGY = {"cabecalho_inicio", "cabecalho_fim"}
PAIR_LABELS = [
    Label(start=0, end=5, category="cabecalho_inicio"),
    Label(start=10, end=15, category="cabecalho_fim"),
]
SOURCE_COMMIT = "a" * 40
LOCK_HASH = "b" * 64
SINGLE_TRIBUNAL_KNOWN_LIMITATIONS = [
    KnownLimitation(gate="multiple_tribunals", reason="TJRO-only for v8.1"),
    KnownLimitation(gate="multiple_source_systems", reason="tjro_juris-only for v8.1"),
]


def _text_for(role: str, index: int) -> str:
    return f"0123{role}{index:03d}89ABCDEFGHIJ"


def _build_release(tmp_path: Path):
    store = SegmenterDatasetStore(tmp_path)
    train_ids: set[str] = set()
    val_ids: set[str] = set()
    test_ids: set[str] = set()

    for index in range(10):
        document = make_document(text=_text_for("train", index), source_uri=f"train-{index}")
        store.write_document(document)
        store.write_annotation(
            make_annotation(
                document, labels=PAIR_LABELS, covered_categories=tuple(sorted(ONTOLOGY))
            )
        )
        train_ids.add(document.document_id)

    for role, count, ids in (("val", 5, val_ids), ("test", 5, test_ids)):
        for index in range(count):
            document = make_document(text=_text_for(role, index), source_uri=f"{role}-{index}")
            store.write_document(document)
            annotation_a = make_annotation(
                document,
                annotator_id="run-a",
                model_family="fam-a",
                completed_at="2026-01-01T00:00:00Z",
                labels=PAIR_LABELS,
                covered_categories=tuple(sorted(ONTOLOGY)),
            )
            annotation_b = make_annotation(
                document,
                annotator_id="run-b",
                model_family="fam-b",
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
        train_ids=frozenset(train_ids), val_ids=frozenset(val_ids), test_ids=frozenset(test_ids)
    )
    documents = store.list_documents()
    keys = [GroupingKeys.from_document(document) for document in documents]
    groups = build_groups(documents, keys, near_duplicate_threshold=0.99)
    split_manifest = create_split_manifest(
        assignment, groups, seed=7, train_ratio=0.70, val_ratio=0.15, near_duplicate_threshold=0.99
    )
    manifest = build_dataset_release(
        store,
        release_id="segmenter-silver-v8.1",
        ontology_version="segmenter-ontology-v8.0.0",
        guideline_version="g1",
        source_commit=SOURCE_COMMIT,
        dependency_lock_hash=LOCK_HASH,
        ci_provider="github-actions",
        ci_run_id="1",
        ontology_categories=ONTOLOGY,
        split_manifest=split_manifest,
        known_limitations=SINGLE_TRIBUNAL_KNOWN_LIMITATIONS,
        iaa_seed=1,
        iaa_resamples=50,
    )
    return store, manifest


def test_resolve_release_documents_matches_pinned_resolutions(tmp_path: Path) -> None:
    store, manifest = _build_release(tmp_path)
    resolved = resolve_release_documents(store, manifest)

    assert len(resolved["train"]) == 10
    assert len(resolved["validation"]) == 5
    assert len(resolved["test"]) == 5
    for _document, labels in resolved["train"] + resolved["validation"] + resolved["test"]:
        assert labels == PAIR_LABELS


def test_resolve_release_documents_ignores_later_store_edits(tmp_path: Path) -> None:
    """A release pins specific annotation/review IDs -- edits to the store after the
    release was built (e.g. a later re-annotation) must not silently change what a
    training export produces for that release.
    """
    store, manifest = _build_release(tmp_path)

    document = make_document(text=_text_for("train", 0), source_uri="train-0")
    later_labels = [Label(start=0, end=5, category="cabecalho_inicio")]
    store.write_annotation(
        make_annotation(
            document,
            annotator_id="run-later",
            labels=later_labels,
            covered_categories=tuple(sorted(ONTOLOGY)),
            completed_at="2027-01-01T00:00:00Z",
        )
    )

    resolved = resolve_release_documents(store, manifest)
    train_labels_by_doc = {doc.document_id: labels for doc, labels in resolved["train"]}
    assert train_labels_by_doc[document.document_id] == PAIR_LABELS


def test_to_opf_record_sorts_labels_and_carries_provenance() -> None:
    document = make_document(text="0123456789ABCDEF")
    unsorted_labels = [
        Label(start=10, end=15, category="cabecalho_fim"),
        Label(start=0, end=5, category="cabecalho_inicio"),
    ]

    record = to_opf_record(document, unsorted_labels)

    assert record["text"] == document.text
    assert record["label"] == [
        {"category": "cabecalho_inicio", "start": 0, "end": 5},
        {"category": "cabecalho_fim", "start": 10, "end": 15},
    ]
    assert record["info"]["document_id"] == document.document_id
    assert record["info"]["tribunal"] == document.source.tribunal


def test_write_label_space_puts_o_first_and_sorts_categories(tmp_path: Path) -> None:
    path = tmp_path / "label_space.json"
    write_label_space(path, {"resultado", "dispositivo_abertura"}, "segmenter-ontology-v8.0.0")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["span_class_names"] == ["O", "dispositivo_abertura", "resultado"]
    assert payload["category_version"] == "segmenter-ontology-v8.0.0"


def test_export_release_for_training_writes_expected_files_and_counts(tmp_path: Path) -> None:
    store, manifest = _build_release(tmp_path)
    output_dir = tmp_path / "artifacts"

    counts = export_release_for_training(store, manifest, output_dir, ONTOLOGY)

    assert counts == {"train": 10, "val": 5, "test": 5}
    for filename, expected_count in (("train", 10), ("val", 5), ("test", 5)):
        lines = (output_dir / f"{filename}.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == expected_count
        for line in lines:
            record = json.loads(line)
            assert record["label"] == [
                {"category": "cabecalho_inicio", "start": 0, "end": 5},
                {"category": "cabecalho_fim", "start": 10, "end": 15},
            ]

    label_space = json.loads((output_dir / "label_space.json").read_text(encoding="utf-8"))
    assert label_space["span_class_names"][0] == "O"
    assert set(label_space["span_class_names"][1:]) == ONTOLOGY
