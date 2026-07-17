"""Tests for prepare_privacy_filter_dataset.py's readiness gates and the
cross-split duplicate check (promote_gold's train/val/test leak guard).
"""

from __future__ import annotations

import json

import pytest

from scripts.prepare_privacy_filter_dataset import (
    GATE_IDS,
    _check_readiness_gates,
    _find_cross_split_duplicates,
    _verification_breakdown,
    promote_gold,
)


def _write_jsonl(path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def test_check_readiness_gates_returns_tagged_tuples() -> None:
    split_counts = {"train": 1, "val": 1, "test": 1}
    per_split_cats = {"train": {}, "val": {}, "test": {}}
    failures = _check_readiness_gates(split_counts, per_split_cats, ["O", "resultado"], {})
    assert failures  # everything is under-supplied, should fail multiple gates
    gate_ids_seen = {gate_id for gate_id, _msg in failures}
    assert gate_ids_seen <= set(GATE_IDS)
    assert "G1" in gate_ids_seen  # zero examples for "resultado" in every split


def test_check_readiness_gates_all_pass() -> None:
    split_counts = {"train": 50, "val": 50, "test": 50}
    per_split_cats = {
        "train": {"resultado": 20},
        "val": {"resultado": 20},
        "test": {"resultado": 20},
    }
    manifest = {"tribunals": {"TJRO": 1, "TJAC": 1, "TJAM": 1}}
    failures = _check_readiness_gates(split_counts, per_split_cats, ["O", "resultado"], manifest)
    assert failures == []


def test_gate_g4_failure_is_independently_identifiable() -> None:
    # Enough volume/support to clear G1/G2/G5, but only 1 tribunal -- only
    # G4 should fail, and it must be tagged "G4" so a caller can waive it
    # specifically without touching the others.
    split_counts = {"train": 200, "val": 200, "test": 200}
    per_split_cats = {
        "train": {"resultado": 20},
        "val": {"resultado": 20},
        "test": {"resultado": 20},
    }
    manifest = {"tribunals": {"TJRO": 1}}
    failures = _check_readiness_gates(split_counts, per_split_cats, ["O", "resultado"], manifest)
    gate_ids_seen = {gate_id for gate_id, _msg in failures}
    assert gate_ids_seen == {"G4"}


def test_find_cross_split_duplicates_detects_shared_doc_id(tmp_path) -> None:
    _write_jsonl(
        tmp_path / "train.jsonl",
        [{"text": "doc a text", "label": [], "info": {"doc_id": "shared_id"}}],
    )
    _write_jsonl(
        tmp_path / "val.jsonl",
        [{"text": "doc a text but different", "label": [], "info": {"doc_id": "shared_id"}}],
    )
    _write_jsonl(tmp_path / "test.jsonl", [])

    problems = _find_cross_split_duplicates(tmp_path)
    assert any("shared_id" in p and "more than one split" in p for p in problems)


def test_find_cross_split_duplicates_detects_identical_text(tmp_path) -> None:
    _write_jsonl(
        tmp_path / "train.jsonl",
        [{"text": "identical body text", "label": [], "info": {"doc_id": "a"}}],
    )
    _write_jsonl(
        tmp_path / "val.jsonl",
        [{"text": "identical body text", "label": [], "info": {"doc_id": "b"}}],
    )
    _write_jsonl(tmp_path / "test.jsonl", [])

    problems = _find_cross_split_duplicates(tmp_path)
    assert any("identical document text" in p for p in problems)


def test_find_cross_split_duplicates_clean_splits_pass(tmp_path) -> None:
    _write_jsonl(
        tmp_path / "train.jsonl",
        [{"text": "train doc", "label": [], "info": {"doc_id": "train_1"}}],
    )
    _write_jsonl(
        tmp_path / "val.jsonl",
        [{"text": "val doc", "label": [], "info": {"doc_id": "val_1"}}],
    )
    _write_jsonl(
        tmp_path / "test.jsonl",
        [{"text": "test doc", "label": [], "info": {"doc_id": "test_1"}}],
    )

    assert _find_cross_split_duplicates(tmp_path) == []


def test_find_cross_split_duplicates_same_doc_id_within_one_split_is_not_a_leak(tmp_path) -> None:
    # Two records sharing a doc_id within the SAME split isn't a train/eval
    # leak (that's a different bug, if any) -- only cross-split duplication
    # is this check's concern.
    _write_jsonl(
        tmp_path / "train.jsonl",
        [
            {"text": "a", "label": [], "info": {"doc_id": "dup"}},
            {"text": "b", "label": [], "info": {"doc_id": "dup"}},
        ],
    )
    _write_jsonl(tmp_path / "val.jsonl", [])
    _write_jsonl(tmp_path / "test.jsonl", [])

    assert _find_cross_split_duplicates(tmp_path) == []


def test_gate_ids_constant_matches_what_check_readiness_gates_emits() -> None:
    split_counts = {"train": 1, "val": 1, "test": 1}
    per_split_cats = {"train": {}, "val": {}, "test": {}}
    manifest = {}
    failures = _check_readiness_gates(split_counts, per_split_cats, ["O", "resultado"], manifest)
    gate_ids_seen = {gate_id for gate_id, _msg in failures}
    assert gate_ids_seen.issubset(set(GATE_IDS))


@pytest.mark.parametrize("gate", GATE_IDS)
def test_each_gate_id_is_a_recognized_string(gate: str) -> None:
    assert gate.startswith("G")
    assert gate[1:].isdigit()


def test_verification_breakdown_counts_verified_vs_provisional(tmp_path) -> None:
    _write_jsonl(
        tmp_path / "val.jsonl",
        [
            {"text": "a", "label": [], "info": {"doc_id": "tjro_acordao_03", "verified": True}},
            {
                "text": "b",
                "label": [],
                "info": {"doc_id": "tjro_juris_2023_09_1", "verified": False},
            },
            {"text": "c", "label": [], "info": {}},  # unmarked -- pre-migration record
        ],
    )
    _write_jsonl(tmp_path / "test.jsonl", [])

    breakdown = _verification_breakdown(tmp_path)
    assert breakdown["val"] == {"verified": 1, "provisional": 1, "unmarked": 1}
    assert breakdown["test"] == {"verified": 0, "provisional": 0, "unmarked": 0}


def test_verification_breakdown_missing_split_file_is_zero(tmp_path) -> None:
    breakdown = _verification_breakdown(tmp_path)
    assert breakdown["val"] == {"verified": 0, "provisional": 0, "unmarked": 0}
    assert breakdown["test"] == {"verified": 0, "provisional": 0, "unmarked": 0}


def test_verification_breakdown_matches_real_gold_split_convention() -> None:
    # Sanity check against the real corpus: only the original 20-doc seed's
    # val+test (doc_ids like tjro_acordao_NN / tjro_sentenca_NN) are
    # ensemble-verified; everything from later rounds is provisional.
    from pathlib import Path

    gold_dir = Path(__file__).resolve().parents[1] / "data" / "segmenter_splits"
    if not (gold_dir / "val.jsonl").exists():
        pytest.skip("real gold data not present in this checkout")
    breakdown = _verification_breakdown(gold_dir)
    assert breakdown["val"]["unmarked"] == 0
    assert breakdown["test"]["unmarked"] == 0
    assert breakdown["val"]["verified"] > 0
    assert breakdown["val"]["provisional"] > 0


def test_promote_gold_rejects_unknown_skip_gate_id(tmp_path) -> None:
    # Required files just need to exist for promote_gold to reach the
    # skip_gates validation, which happens before any content is read.
    for name in ("train.jsonl", "val.jsonl", "test.jsonl", "label_space.json"):
        (tmp_path / name).write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown gate id"):
        promote_gold(tmp_path, tmp_path / "out", skip_gates=frozenset({"G3"}))
