"""Tests for scripts.synthetic_segmenter.compose_mix."""

from __future__ import annotations

import json

from scripts.synthetic_segmenter.compose_mix import compose_mix, write_mix


def _records(source_type: str, n: int) -> list[dict]:
    return [
        {"text": f"{source_type} doc {i}", "label": [], "info": {"source_type": source_type}}
        for i in range(n)
    ]


def test_compose_mix_respects_relative_weights() -> None:
    pools = {
        "pristine_real": _records("pristine_real", 100),
        "synthetic": _records("synthetic", 100),
    }
    weights = {"pristine_real": 4.0, "synthetic": 1.0}
    _records_out, manifest = compose_mix(
        pools, weights, seed=1, mix_id="test-mix", corpus_release_ids=["v1-001"], target_total=100
    )
    assert manifest["counts_by_source_type"]["pristine_real"] == 80
    assert manifest["counts_by_source_type"]["synthetic"] == 20


def test_compose_mix_oversamples_when_pool_smaller_than_target() -> None:
    pools = {"synthetic": _records("synthetic", 5)}
    weights = {"synthetic": 1.0}
    records, manifest = compose_mix(
        pools, weights, seed=1, mix_id="test-mix", corpus_release_ids=["v1-001"], target_total=20
    )
    assert len(records) == 20
    assert manifest["counts_by_source_type"]["synthetic"] == 20
    # every original record appears at least once
    seen_texts = {r["text"] for r in records}
    assert seen_texts == {r["text"] for r in pools["synthetic"]}


def test_compose_mix_source_in_pools_but_not_weights_is_excluded() -> None:
    pools = {"pristine_real": _records("pristine_real", 10), "synthetic": _records("synthetic", 10)}
    weights = {"pristine_real": 1.0}
    records, manifest = compose_mix(
        pools, weights, seed=1, mix_id="test-mix", corpus_release_ids=["v1-001"]
    )
    assert all(r["info"]["source_type"] == "pristine_real" for r in records)
    assert "synthetic" not in manifest["counts_by_source_type"]


def test_compose_mix_source_in_weights_but_not_pools_is_empty() -> None:
    pools = {"pristine_real": _records("pristine_real", 10)}
    weights = {"pristine_real": 1.0, "hybrid": 1.0}
    records, manifest = compose_mix(
        pools, weights, seed=1, mix_id="test-mix", corpus_release_ids=["v1-001"]
    )
    assert manifest["counts_by_source_type"]["hybrid"] == 0
    assert all(r["info"]["source_type"] != "hybrid" for r in records)


def test_compose_mix_zero_total_weight_raises() -> None:
    import pytest

    pools = {"pristine_real": _records("pristine_real", 10)}
    with pytest.raises(ValueError, match="positive number"):
        compose_mix(pools, {"pristine_real": 0.0}, seed=1, mix_id="x", corpus_release_ids=["v1"])


def test_compose_mix_is_deterministic() -> None:
    pools = {"pristine_real": _records("pristine_real", 20), "synthetic": _records("synthetic", 20)}
    weights = {"pristine_real": 2.0, "synthetic": 1.0}
    first, _m1 = compose_mix(pools, weights, seed=42, mix_id="x", corpus_release_ids=["v1"])
    second, _m2 = compose_mix(pools, weights, seed=42, mix_id="x", corpus_release_ids=["v1"])
    assert first == second


def test_compose_mix_manifest_records_pristine_real_doc_ids() -> None:
    pools = {
        "pristine_real": [
            {"text": "a", "label": [], "info": {"doc_id": "doc_a"}},
            {"text": "b", "label": [], "info": {"doc_id": "doc_b"}},
        ]
    }
    weights = {"pristine_real": 1.0}
    _records_out, manifest = compose_mix(
        pools, weights, seed=1, mix_id="x", corpus_release_ids=["v1"]
    )
    assert manifest["source_doc_ids_pristine_real"] == ["doc_a", "doc_b"]


def test_compose_mix_manifest_carries_corpus_release_ids_and_mix_id() -> None:
    pools = {"pristine_real": _records("pristine_real", 5)}
    weights = {"pristine_real": 1.0}
    _records_out, manifest = compose_mix(
        pools,
        weights,
        seed=1,
        mix_id="run_D_seed_3",
        corpus_release_ids=["v2-20260715-001", "v2-20260716-002"],
        curriculum_stage="adversarial_heavy",
    )
    assert manifest["mix_id"] == "run_D_seed_3"
    assert manifest["corpus_release_ids"] == ["v2-20260715-001", "v2-20260716-002"]
    assert manifest["curriculum_stage"] == "adversarial_heavy"


def test_compose_mix_default_target_total_sums_weighted_pools() -> None:
    pools = {"pristine_real": _records("pristine_real", 10), "synthetic": _records("synthetic", 30)}
    weights = {"pristine_real": 1.0, "synthetic": 1.0}
    records, manifest = compose_mix(pools, weights, seed=1, mix_id="x", corpus_release_ids=["v1"])
    assert manifest["total_records"] == 40
    assert len(records) == 40


def test_write_mix_writes_jsonl_and_manifest(tmp_path) -> None:
    records = [{"text": "a", "label": [], "info": {}}, {"text": "b", "label": [], "info": {}}]
    manifest = {"mix_id": "x", "total_records": 2}
    output_path = tmp_path / "train.jsonl"
    manifest_path = tmp_path / "mix_manifest.json"

    write_mix(records, manifest, output_path=output_path, manifest_path=manifest_path)

    lines = output_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0])["text"] == "a"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["mix_id"] == "x"


def test_write_mix_creates_parent_directories(tmp_path) -> None:
    output_path = tmp_path / "nested" / "dir" / "train.jsonl"
    manifest_path = tmp_path / "other" / "manifest.json"
    write_mix([], {"mix_id": "x"}, output_path=output_path, manifest_path=manifest_path)
    assert output_path.exists()
    assert manifest_path.exists()
