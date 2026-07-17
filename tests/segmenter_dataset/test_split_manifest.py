from __future__ import annotations

from conftest import make_document

from segmenter_dataset.splits import (
    GroupingKeys,
    SplitAssignment,
    build_groups,
    create_split_manifest,
)


def test_grouping_keys_are_loaded_from_document_records() -> None:
    first = make_document(
        source_uri="u1",
        text="documento A",
        normalized_process_number="0001234",
    )
    second = make_document(
        source_uri="u2",
        text="documento B completamente diferente",
        normalized_process_number="0001234",
    )

    keys = [
        GroupingKeys.from_document(first),
        GroupingKeys.from_document(second),
    ]
    groups = build_groups([first, second], keys)

    assert len(groups) == 1


def test_split_manifest_records_reproducibility_parameters() -> None:
    assignment = SplitAssignment(
        train_ids=frozenset({"doc_a"}),
        val_ids=frozenset({"doc_b"}),
        test_ids=frozenset({"doc_c"}),
    )
    groups = {
        "doc_a": frozenset({"doc_a"}),
        "doc_b": frozenset({"doc_b"}),
        "doc_c": frozenset({"doc_c"}),
    }

    manifest = create_split_manifest(
        assignment,
        groups,
        seed=42,
        train_ratio=0.70,
        val_ratio=0.15,
        near_duplicate_threshold=0.91,
    )

    assert manifest.seed == 42
    assert manifest.train_ratio == 0.70
    assert manifest.val_ratio == 0.15
    assert manifest.near_duplicate_threshold == 0.91
    assert manifest.groups["doc_a"] == ("doc_a",)
