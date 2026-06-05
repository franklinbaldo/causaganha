"""Tests for v7 region reconstruction from OPF anchor spans."""

from __future__ import annotations

from scripts.reconstruct_regions import (
    Region,
    pair_inicio_fim,
    reconstruct_regions,
    reconstruct_single_anchor_regions,
    validate_anchor_lengths,
)


TEXT = (
    "EMENTA: Apelacao. Direito civil. "
    "RELATORIO: Cuida-se de recurso. "
    "Ante o exposto, julgo procedente. "
    "HONORARIOS: 10%. "
    "CUSTAS: pelo vencido. "
    "ENCERRAMENTO: Publique-se."
)
TEXT_LEN = len(TEXT)


def _find(surface: str) -> tuple[int, int]:
    idx = TEXT.find(surface)
    assert idx >= 0, f"{surface!r} not found"
    return idx, idx + len(surface)


class TestValidateAnchorLengths:
    def test_short_spans_pass(self) -> None:
        s, e = _find("Ante o exposto")
        spans = [{"category": "dispositivo_abertura", "start": s, "end": e}]
        assert validate_anchor_lengths(spans, TEXT) == []

    def test_long_single_anchor_warns(self) -> None:
        spans = [{"category": "dispositivo_abertura", "start": 0, "end": 200}]
        warnings = validate_anchor_lengths(spans, TEXT, max_chars=50)
        assert len(warnings) == 1
        assert "200 chars" in warnings[0]

    def test_paired_categories_not_checked(self) -> None:
        spans = [{"category": "ementa_inicio", "start": 0, "end": 200}]
        assert validate_anchor_lengths(spans, TEXT) == []


class TestPairInicioFim:
    def test_matched_pair(self) -> None:
        si, ei = _find("EMENTA:")
        sf, ef = _find("civil.")
        spans = [
            {"category": "ementa_inicio", "start": si, "end": ei},
            {"category": "ementa_fim", "start": sf, "end": ef},
        ]
        regions = pair_inicio_fim(spans, TEXT_LEN)
        assert len(regions) == 1
        assert regions[0] == Region("ementa", si, ef, matched=True)

    def test_unmatched_inicio_extends_to_eod(self) -> None:
        si, ei = _find("HONORARIOS:")
        spans = [{"category": "honorarios_inicio", "start": si, "end": ei}]
        regions = pair_inicio_fim(spans, TEXT_LEN)
        assert len(regions) == 1
        assert regions[0].end == TEXT_LEN
        assert regions[0].matched is False

    def test_multiple_pairs_same_base(self) -> None:
        spans = [
            {"category": "ementa_inicio", "start": 0, "end": 5},
            {"category": "ementa_fim", "start": 10, "end": 15},
            {"category": "ementa_inicio", "start": 20, "end": 25},
            {"category": "ementa_fim", "start": 30, "end": 35},
        ]
        regions = pair_inicio_fim(spans, 100)
        assert len(regions) == 2
        assert all(r.matched for r in regions)
        assert regions[0].start == 0
        assert regions[0].end == 15
        assert regions[1].start == 20
        assert regions[1].end == 35

    def test_no_spans_returns_empty(self) -> None:
        assert pair_inicio_fim([], TEXT_LEN) == []


class TestReconstructSingleAnchor:
    def test_single_anchor_tiling(self) -> None:
        sd, ed = _find("Ante o exposto")
        sr, er = _find("julgo procedente")
        spans = [
            {"category": "dispositivo_abertura", "start": sd, "end": ed},
            {"category": "resultado", "start": sr, "end": er},
        ]
        regions = reconstruct_single_anchor_regions(spans, TEXT_LEN)
        assert len(regions) == 2
        assert regions[0].category == "dispositivo_abertura"
        assert regions[0].start == sd
        assert regions[0].end == sr
        assert regions[1].category == "resultado"
        assert regions[1].start == sr
        assert regions[1].end == TEXT_LEN

    def test_empty_spans(self) -> None:
        assert reconstruct_single_anchor_regions([], TEXT_LEN) == []


class TestReconstructRegions:
    def test_combines_paired_and_single(self) -> None:
        si, ei = _find("EMENTA:")
        sf, ef = _find("civil.")
        sd, ed = _find("Ante o exposto")
        spans = [
            {"category": "ementa_inicio", "start": si, "end": ei},
            {"category": "ementa_fim", "start": sf, "end": ef},
            {"category": "dispositivo_abertura", "start": sd, "end": ed},
        ]
        regions = reconstruct_regions(spans, TEXT_LEN)
        assert len(regions) == 2
        cats = [r.category for r in regions]
        assert "ementa" in cats
        assert "dispositivo_abertura" in cats
        assert regions[0].start < regions[1].start
