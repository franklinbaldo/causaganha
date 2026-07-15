"""Tests for scripts.synthetic_segmenter.provenance — RFC 0011 §15 schema."""

from __future__ import annotations

from scripts.synthetic_segmenter.provenance import default_provenance, validate_provenance


def test_pristine_real_needs_no_provenance() -> None:
    assert validate_provenance({}) == []


def test_pristine_real_explicit_source_type_validates() -> None:
    info = default_provenance("pristine_real")
    assert validate_provenance(info) == []


def test_unknown_source_type_rejected() -> None:
    problems = validate_provenance({"source_type": "not_a_real_category"})
    assert len(problems) == 1
    assert "unknown source_type" in problems[0]


def test_fully_synthetic_requires_generator_identity() -> None:
    info = {"source_type": "fully_synthetic", "synthetic": True, "augmented": False}
    problems = validate_provenance(info)
    assert any("generator_version" in p for p in problems)
    assert any("corpus_release_id" in p for p in problems)
    assert any("seed" in p for p in problems)


def test_fully_synthetic_complete_record_validates() -> None:
    info = default_provenance("fully_synthetic")
    info.update({"generator_version": "v2", "corpus_release_id": "v2-20260715-001", "seed": 42})
    assert validate_provenance(info) == []


def test_hybrid_synthetic_requires_source_doc_ids_and_contains_real_text() -> None:
    info = default_provenance("hybrid_synthetic")
    info.update({"generator_version": "v2", "corpus_release_id": "v2-x", "seed": 1})
    problems = validate_provenance(info)
    assert any("source_doc_ids" in p for p in problems)


def test_hybrid_synthetic_complete_record_validates() -> None:
    info = default_provenance("hybrid_synthetic")
    info.update(
        {
            "generator_version": "v2",
            "corpus_release_id": "v2-x",
            "seed": 1,
            "source_doc_ids": ["tjro_acordao_0017"],
        }
    )
    assert validate_provenance(info) == []


def test_augmented_real_requires_exactly_one_parent() -> None:
    info = default_provenance("augmented_real")
    info["source_doc_ids"] = ["parent_1", "parent_2"]
    problems = validate_provenance(info)
    assert any("exactly one parent" in p for p in problems)


def test_augmented_real_single_parent_validates() -> None:
    info = default_provenance("augmented_real")
    info["source_doc_ids"] = ["parent_1"]
    assert validate_provenance(info) == []


def test_fixed_value_mismatch_flagged() -> None:
    info = default_provenance("fully_synthetic")
    info.update({"generator_version": "v2", "corpus_release_id": "v2-x", "seed": 1})
    info["contains_real_text"] = True  # fully_synthetic must be False
    problems = validate_provenance(info)
    assert any("contains_real_text" in p for p in problems)


def test_unmatched_pair_must_be_bool() -> None:
    info = default_provenance("pristine_real")
    info["unmatched_pair"] = "yes"
    problems = validate_provenance(info)
    assert any("unmatched_pair" in p for p in problems)


def test_hard_negative_families_must_be_list() -> None:
    info = default_provenance("pristine_real")
    info["hard_negative_families"] = "quoted_dispositivo"
    problems = validate_provenance(info)
    assert any("hard_negative_families" in p for p in problems)


def test_default_provenance_rejects_unknown_category() -> None:
    import pytest

    with pytest.raises(ValueError, match="unknown source_type"):
        default_provenance("not_a_category")
