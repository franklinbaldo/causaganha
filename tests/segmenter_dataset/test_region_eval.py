"""Tests for region-level evaluation (#1052): does an anchor error damage the
reconstructed structural region the product actually consumes?
"""

from __future__ import annotations

from segmenter_dataset.region_eval import (
    RegionComparison,
    compare_regions,
    region_match_rate,
    regions_from_labels,
)
from segmenter_dataset.schemas import Label


def _label(start: int, end: int, category: str) -> Label:
    return Label(start=start, end=end, category=category)


def test_regions_from_labels_matched_pair_spans_inicio_start_to_fim_end() -> None:
    labels = (
        _label(10, 20, "relatorio_inicio"),
        _label(80, 90, "relatorio_fim"),
    )

    regions = regions_from_labels(labels)

    assert regions == {"relatorio": (10, 90)}


def test_regions_from_labels_unmatched_inicio_uses_its_own_span() -> None:
    labels = (_label(10, 20, "relatorio_inicio"),)

    regions = regions_from_labels(labels)

    assert regions == {"relatorio": (10, 20)}


def test_regions_from_labels_unmatched_fim_uses_its_own_span() -> None:
    labels = (_label(80, 90, "relatorio_fim"),)

    regions = regions_from_labels(labels)

    assert regions == {"relatorio": (80, 90)}


def test_regions_from_labels_ignores_single_anchor_categories() -> None:
    labels = (_label(0, 5, "ref_processual"),)

    regions = regions_from_labels(labels)

    assert regions == {}


def test_regions_from_labels_handles_multiple_bases_independently() -> None:
    labels = (
        _label(0, 10, "relatorio_inicio"),
        _label(40, 50, "relatorio_fim"),
        _label(60, 70, "voto_inicio"),
        _label(90, 100, "voto_fim"),
    )

    regions = regions_from_labels(labels)

    assert regions == {"relatorio": (0, 50), "voto": (60, 100)}


def test_compare_regions_perfect_match_has_zero_error_and_full_iou() -> None:
    gold = (_label(0, 10, "relatorio_inicio"), _label(40, 50, "relatorio_fim"))
    predicted = (_label(0, 10, "relatorio_inicio"), _label(40, 50, "relatorio_fim"))

    [result] = compare_regions(gold, predicted)

    assert result == RegionComparison(
        base="relatorio", gold=(0, 50), predicted=(0, 50), start_error=0, end_error=0, iou=1.0
    )
    assert result.matched is True


def test_compare_regions_shifted_boundaries_report_errors_and_partial_iou() -> None:
    gold = (_label(0, 10, "relatorio_inicio"), _label(40, 50, "relatorio_fim"))
    # predicted region is (5, 50): 5 later start, same end -> overlap 45, union 50
    predicted = (_label(5, 15, "relatorio_inicio"), _label(40, 50, "relatorio_fim"))

    [result] = compare_regions(gold, predicted)

    assert result.start_error == 5
    assert result.end_error == 0
    assert result.iou == 45 / 50
    assert result.matched is True


def test_compare_regions_missing_prediction_is_unmatched_not_zero_error() -> None:
    gold = (_label(0, 10, "relatorio_inicio"), _label(40, 50, "relatorio_fim"))

    [result] = compare_regions(gold, predicted_labels=())

    assert result.gold == (0, 50)
    assert result.predicted is None
    assert result.start_error is None
    assert result.end_error is None
    assert result.iou == 0.0
    assert result.matched is False


def test_compare_regions_spurious_prediction_is_unmatched() -> None:
    predicted = (_label(0, 10, "relatorio_inicio"), _label(40, 50, "relatorio_fim"))

    [result] = compare_regions(gold_labels=(), predicted_labels=predicted)

    assert result.gold is None
    assert result.predicted == (0, 50)
    assert result.matched is False


def test_compare_regions_reports_every_base_from_either_side_sorted() -> None:
    gold = (_label(0, 10, "relatorio_inicio"), _label(40, 50, "relatorio_fim"))
    predicted = (_label(60, 70, "voto_inicio"), _label(90, 100, "voto_fim"))

    results = compare_regions(gold, predicted)

    assert [r.base for r in results] == ["relatorio", "voto"]
    assert results[0].matched is False
    assert results[1].matched is False


def test_region_match_rate_all_matched_is_one() -> None:
    gold = (_label(0, 10, "relatorio_inicio"), _label(40, 50, "relatorio_fim"))
    predicted = (_label(0, 10, "relatorio_inicio"), _label(40, 50, "relatorio_fim"))

    rate = region_match_rate(compare_regions(gold, predicted))

    assert rate == 1.0


def test_region_match_rate_none_matched_is_zero_not_none() -> None:
    gold = (_label(0, 10, "relatorio_inicio"), _label(40, 50, "relatorio_fim"))

    rate = region_match_rate(compare_regions(gold, predicted_labels=()))

    assert rate == 0.0


def test_region_match_rate_empty_gold_is_none_not_zero() -> None:
    predicted = (_label(0, 10, "relatorio_inicio"), _label(40, 50, "relatorio_fim"))

    rate = region_match_rate(compare_regions(gold_labels=(), predicted_labels=predicted))

    assert rate is None
