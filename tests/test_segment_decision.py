"""Integration tests for the end-to-end inference pipeline (segment_decision).

These run the GPU-free stages — ref_normativa regex merge + region
reconstruction — over the committed gold splits, asserting the invariants
that matter for the product output (regions), not just the anchor spans.
"""

from __future__ import annotations

import json
from itertools import pairwise
from pathlib import Path

import pytest

from scripts.prepare_privacy_filter_dataset import (
    _PAIRED_REGION_BASES,
    SINGLE_ANCHOR_CATEGORIES,
)
from scripts.ref_normativa_prepass import extract_ref_normativa, merge_with_opf_spans
from scripts.segment_decision import segment_text


GOLD_DIR = Path("data/segmenter_splits")

_REGION_CATEGORIES = frozenset(SINGLE_ANCHOR_CATEGORIES) | frozenset(_PAIRED_REGION_BASES)


def _gold_records() -> list[dict]:
    records: list[dict] = []
    for split in ("train", "val", "test"):
        path = GOLD_DIR / f"{split}.jsonl"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    records.append(json.loads(stripped))
    return records


GOLD = _gold_records()

pytestmark = pytest.mark.skipif(not GOLD, reason="gold splits not present")


class TestSegmentTextOnGold:
    def test_merged_spans_have_no_overlaps(self) -> None:
        for rec in GOLD:
            result = segment_text(rec["text"], rec["label"])
            spans = sorted(result["spans"], key=lambda s: s["start"])
            for a, b in pairwise(spans):
                assert b["start"] >= a["end"], (
                    f"overlap after merge: [{a['category']}]({a['start']}:{a['end']}) "
                    f"vs [{b['category']}]({b['start']}:{b['end']})"
                )

    def test_gold_spans_survive_ref_normativa_merge(self) -> None:
        # The regex pre-pass must never displace a model/gold span — gold
        # spans sort first at equal starts and ref spans overlapping them
        # are dropped by the merge.
        for rec in GOLD:
            result = segment_text(rec["text"], rec["label"])
            kept = {(s["category"], s["start"], s["end"]) for s in result["spans"]}
            gold_set = {(s["category"], s["start"], s["end"]) for s in rec["label"]}
            dropped = gold_set - kept
            # A gold span may only be dropped if another gold span overlapped
            # it (already prevented by opf_annotate validate), never by a
            # ref_normativa regex span.
            assert not dropped, f"gold spans dropped by merge: {dropped}"

    def test_regions_are_within_bounds_and_ordered(self) -> None:
        for rec in GOLD:
            text = rec["text"]
            result = segment_text(text, rec["label"])
            for region in result["regions"]:
                assert 0 <= region["start"] < region["end"] <= len(text), (
                    f"bad region bounds: {region}"
                )
                assert region["category"] in _REGION_CATEGORIES, (
                    f"unexpected region category: {region['category']}"
                )

    def test_every_paired_inicio_yields_a_region(self) -> None:
        for rec in GOLD:
            result = segment_text(rec["text"], rec["label"])
            inicio_counts: dict[str, int] = {}
            for sp in rec["label"]:
                cat = sp["category"]
                if cat.endswith("_inicio"):
                    base = cat.removesuffix("_inicio")
                    inicio_counts[base] = inicio_counts.get(base, 0) + 1
            region_counts: dict[str, int] = {}
            for region in result["regions"]:
                if region["category"] in _PAIRED_REGION_BASES:
                    region_counts[region["category"]] = region_counts.get(region["category"], 0) + 1
            for base, n in inicio_counts.items():
                assert region_counts.get(base, 0) == n, (
                    f"{base}: {n} _inicio anchors but {region_counts.get(base, 0)} regions"
                )

    def test_ref_normativa_appears_in_output_not_gold(self) -> None:
        # Gold never labels ref_normativa (regex pre-pass owns it); after the
        # pipeline it must be present whenever the text cites statutes.
        found_any = False
        for rec in GOLD:
            assert all(s["category"] != "ref_normativa" for s in rec["label"])
            result = segment_text(rec["text"], rec["label"])
            if any(s["category"] == "ref_normativa" for s in result["spans"]):
                found_any = True
        assert found_any, (
            "no ref_normativa span produced over the entire gold corpus — "
            "regex pre-pass is likely broken"
        )


class TestMergeSemantics:
    def test_ref_span_overlapping_model_span_is_dropped(self) -> None:
        text = "Nos termos do art. 927 do CPC, julgo procedente."
        s = text.find("art. 927")
        model = [{"category": "fundamentacao_legal", "start": s, "end": s + len("art. 927")}]
        ref = extract_ref_normativa(text)
        assert ref, "regex should find art. 927 / CPC"
        merged = merge_with_opf_spans(model, ref)
        fund = [sp for sp in merged if sp["category"] == "fundamentacao_legal"]
        assert len(fund) == 1
        for a, b in pairwise(sorted(merged, key=lambda x: x["start"])):
            assert b["start"] >= a["end"]

    def test_ref_span_in_clear_text_is_kept(self) -> None:
        text = "Aplica-se a Súmula 331 do TST ao caso."
        merged = merge_with_opf_spans([], extract_ref_normativa(text))
        assert any(sp["category"] == "ref_normativa" for sp in merged)
