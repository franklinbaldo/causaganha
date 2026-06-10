"""Tests for the verification-ensemble mechanical comparator."""

from __future__ import annotations

from scripts.ensemble_compare import compare_record


def _sp(cat: str, start: int, end: int) -> dict:
    return {"category": cat, "start": start, "end": end}


class TestCompareRecord:
    def test_identical_sets_agree(self) -> None:
        spans = [_sp("resultado", 10, 25), _sp("dispositivo_abertura", 0, 14)]
        assert compare_record(spans, list(spans)) == []

    def test_missing_span(self) -> None:
        ref = [_sp("resultado", 10, 25)]
        out = compare_record(ref, [])
        assert len(out) == 1
        assert out[0]["kind"] == "missing"
        assert out[0]["category"] == "resultado"

    def test_extra_span(self) -> None:
        role = [_sp("resultado", 10, 25)]
        out = compare_record([], role)
        assert len(out) == 1
        assert out[0]["kind"] == "extra"

    def test_category_disagreement_same_offsets(self) -> None:
        ref = [_sp("fundamentacao_legal", 5, 20)]
        role = [_sp("resultado", 5, 20)]
        out = compare_record(ref, role)
        kinds = {d["kind"] for d in out}
        assert kinds == {"category"}
        assert out[0]["other_category"] == "resultado"

    def test_boundary_disagreement_same_category(self) -> None:
        ref = [_sp("resultado", 10, 25)]
        role = [_sp("resultado", 10, 30)]
        out = compare_record(ref, role)
        assert len(out) == 1
        assert out[0]["kind"] == "boundary"
        assert out[0]["other_end"] == 30

    def test_disjoint_same_category_is_missing_plus_extra(self) -> None:
        ref = [_sp("resultado", 10, 25)]
        role = [_sp("resultado", 50, 65)]
        kinds = sorted(d["kind"] for d in compare_record(ref, role))
        assert kinds == ["extra", "missing"]
