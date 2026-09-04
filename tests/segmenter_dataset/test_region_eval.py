"""Tests for region-level evaluation (#1052): does an anchor error damage the
reconstructed structural region the product actually consumes?
"""

from __future__ import annotations

from segmenter_dataset.model_eval import MIN_GROUP_SUPPORT_DOCUMENTS, DocumentModelPrediction
from segmenter_dataset.region_eval import (
    RegionComparison,
    RegionGroupMetrics,
    RegionTypeMetrics,
    StructuralAnomaly,
    aggregate_region_metrics,
    bootstrap_region_metric_ci_low,
    collect_structural_anomalies,
    compare_regions,
    detect_inverted_regions,
    region_breakdown_by_group,
    region_match_rate,
    regions_from_labels,
    render_region_report,
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


def _region_prediction(
    doc_id: str,
    gold: list[tuple[int, int, str]],
    predicted: list[tuple[int, int, str]],
) -> DocumentModelPrediction:
    return DocumentModelPrediction(
        document_id=doc_id,
        gold=_labels(gold),
        model_predicted=_labels(predicted),
        baseline_predicted=(),
    )


def _labels(spans: list[tuple[int, int, str]]) -> tuple[Label, ...]:
    return tuple(_label(s, e, c) for s, e, c in spans)


def test_aggregate_region_metrics_perfect_match_across_documents() -> None:
    predictions = [
        _region_prediction(
            "d1",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
        _region_prediction(
            "d2",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
    ]

    report = aggregate_region_metrics(predictions)

    assert report == {
        "relatorio": RegionTypeMetrics(
            base="relatorio",
            support=2,
            matched=2,
            missed=0,
            hallucinated=0,
            match_rate=1.0,
            mean_iou=1.0,
            mean_start_error=0.0,
            mean_end_error=0.0,
        )
    }


def test_aggregate_region_metrics_missed_region_not_counted_as_hallucinated() -> None:
    predictions = [
        _region_prediction("d1", [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")], []),
    ]

    report = aggregate_region_metrics(predictions)

    metrics = report["relatorio"]
    assert metrics.support == 1
    assert metrics.matched == 0
    assert metrics.missed == 1
    assert metrics.hallucinated == 0
    assert metrics.match_rate == 0.0
    assert metrics.mean_iou is None
    assert metrics.mean_start_error is None
    assert metrics.mean_end_error is None


def test_aggregate_region_metrics_hallucinated_region_excluded_from_support() -> None:
    predictions = [
        _region_prediction("d1", [], [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")]),
    ]

    report = aggregate_region_metrics(predictions)

    metrics = report["relatorio"]
    assert metrics.support == 0
    assert metrics.matched == 0
    assert metrics.missed == 0
    assert metrics.hallucinated == 1
    assert metrics.match_rate is None
    assert metrics.mean_iou is None


def test_aggregate_region_metrics_reports_every_base_sorted() -> None:
    predictions = [
        _region_prediction(
            "d1",
            [(60, 70, "voto_inicio"), (90, 100, "voto_fim")],
            [(60, 70, "voto_inicio"), (90, 100, "voto_fim")],
        ),
        _region_prediction(
            "d2",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
    ]

    report = aggregate_region_metrics(predictions)

    assert list(report.keys()) == ["relatorio", "voto"]


def test_aggregate_region_metrics_averages_over_matched_documents_only() -> None:
    predictions = [
        _region_prediction(
            "d1",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
        _region_prediction(
            "d2",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(5, 15, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
        _region_prediction("d3", [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")], []),
    ]

    metrics = aggregate_region_metrics(predictions)["relatorio"]

    assert metrics.support == 3
    assert metrics.matched == 2
    assert metrics.missed == 1
    assert metrics.hallucinated == 0
    assert metrics.match_rate == 2 / 3
    assert metrics.mean_start_error == (0 + 5) / 2
    assert metrics.mean_end_error == 0.0
    assert metrics.mean_iou == (1.0 + 45 / 50) / 2


def test_region_breakdown_by_group_reports_per_group_region_metrics() -> None:
    predictions = [
        _region_prediction(
            f"tjro{i}",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        )
        for i in range(5)
    ] + [_region_prediction("tjsp0", [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")], [])]
    group_of_document = {
        item.document_id: ("tjro" if item.document_id.startswith("tjro") else "tjsp")
        for item in predictions
    }

    breakdown = region_breakdown_by_group(predictions, group_of_document, min_documents=1)

    assert breakdown["tjro"].document_count == 5
    assert breakdown["tjro"].regions == aggregate_region_metrics(predictions[:5])
    assert breakdown["tjsp"].document_count == 1
    assert breakdown["tjsp"].regions == aggregate_region_metrics(predictions[5:])


def test_region_breakdown_by_group_below_min_documents_reports_count_only() -> None:
    predictions = [
        _region_prediction("d1", [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")], [])
    ]
    group_of_document = {"d1": "tst"}

    breakdown = region_breakdown_by_group(predictions, group_of_document, min_documents=5)

    assert breakdown["tst"] == RegionGroupMetrics(group="tst", document_count=1, regions=None)


def test_region_breakdown_by_group_skips_documents_missing_from_mapping() -> None:
    predictions = [
        _region_prediction("d1", [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")], []),
        _region_prediction("d2", [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")], []),
    ]
    group_of_document = {"d1": "tjro"}  # d2 has no known group, e.g. missing source metadata

    breakdown = region_breakdown_by_group(predictions, group_of_document, min_documents=1)

    assert set(breakdown) == {"tjro"}
    assert breakdown["tjro"].document_count == 1


def test_region_breakdown_by_group_default_min_documents_gates_on_document_count() -> None:
    predictions = [
        _region_prediction(f"d{i}", [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")], [])
        for i in range(MIN_GROUP_SUPPORT_DOCUMENTS - 1)
    ]
    group_of_document = {item.document_id: "only" for item in predictions}

    breakdown = region_breakdown_by_group(predictions, group_of_document)

    assert breakdown["only"].document_count == MIN_GROUP_SUPPORT_DOCUMENTS - 1
    assert breakdown["only"].regions is None


def test_region_breakdown_by_group_empty_mapping_is_empty_result() -> None:
    predictions = [
        _region_prediction("d1", [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")], [])
    ]

    assert region_breakdown_by_group(predictions, {}) == {}


def test_bootstrap_region_metric_ci_low_empty_predictions_is_none() -> None:
    ci_low = bootstrap_region_metric_ci_low(
        [], "relatorio", lambda metrics: metrics.match_rate, seed=0
    )

    assert ci_low is None


def test_bootstrap_region_metric_ci_low_unknown_base_is_none() -> None:
    predictions = [
        _region_prediction(
            "d1",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
    ]

    ci_low = bootstrap_region_metric_ci_low(
        predictions, "voto", lambda metrics: metrics.match_rate, seed=0
    )

    assert ci_low is None


def test_bootstrap_region_metric_ci_low_perfect_match_is_one() -> None:
    predictions = [
        _region_prediction(
            f"d{i}",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        )
        for i in range(5)
    ]

    ci_low = bootstrap_region_metric_ci_low(
        predictions, "relatorio", lambda metrics: metrics.match_rate, seed=0, resamples=50
    )

    assert ci_low == 1.0


def test_bootstrap_region_metric_ci_low_is_deterministic_for_same_seed() -> None:
    predictions = [
        _region_prediction(
            "d1",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
        _region_prediction("d2", [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")], []),
        _region_prediction(
            "d3",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(5, 15, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
    ]

    first = bootstrap_region_metric_ci_low(
        predictions, "relatorio", lambda metrics: metrics.match_rate, seed=42, resamples=200
    )
    second = bootstrap_region_metric_ci_low(
        predictions, "relatorio", lambda metrics: metrics.match_rate, seed=42, resamples=200
    )

    assert first == second


def test_bootstrap_region_metric_ci_low_reflects_variance_below_point_estimate() -> None:
    predictions = [
        _region_prediction(
            "d1",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
        _region_prediction(
            "d2",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
        _region_prediction("d3", [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")], []),
    ]
    point_estimate = aggregate_region_metrics(predictions)["relatorio"].match_rate

    ci_low = bootstrap_region_metric_ci_low(
        predictions, "relatorio", lambda metrics: metrics.match_rate, seed=7, resamples=500
    )

    assert ci_low is not None
    assert point_estimate is not None
    assert ci_low < point_estimate


def test_bootstrap_region_metric_ci_low_none_metric_values_are_excluded() -> None:
    predictions = [
        _region_prediction("d1", [], [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")]),
    ]

    ci_low = bootstrap_region_metric_ci_low(
        predictions, "relatorio", lambda metrics: metrics.match_rate, seed=0, resamples=20
    )

    assert ci_low is None


def test_detect_inverted_regions_flags_fim_anchor_before_inicio_anchor() -> None:
    labels = (
        _label(10, 20, "relatorio_fim"),
        _label(50, 60, "relatorio_inicio"),
    )

    anomalies = detect_inverted_regions("d1", labels)

    assert anomalies == [
        StructuralAnomaly(
            document_id="d1",
            base="relatorio",
            inicio=(50, 60),
            fim=(10, 20),
        )
    ]


def test_detect_inverted_regions_normal_order_is_clean() -> None:
    labels = (
        _label(10, 20, "relatorio_inicio"),
        _label(50, 60, "relatorio_fim"),
    )

    assert detect_inverted_regions("d1", labels) == []


def test_detect_inverted_regions_ignores_unmatched_anchors() -> None:
    assert detect_inverted_regions("d1", (_label(10, 20, "relatorio_inicio"),)) == []
    assert detect_inverted_regions("d1", (_label(10, 20, "relatorio_fim"),)) == []


def test_detect_inverted_regions_ignores_single_anchor_categories() -> None:
    labels = (_label(0, 5, "ref_processual"),)

    assert detect_inverted_regions("d1", labels) == []


def test_detect_inverted_regions_reports_every_base_independently_sorted() -> None:
    labels = (
        _label(0, 10, "relatorio_inicio"),
        _label(40, 50, "relatorio_fim"),
        _label(80, 90, "voto_fim"),
        _label(120, 130, "voto_inicio"),
    )

    anomalies = detect_inverted_regions("d1", labels)

    assert [anomaly.base for anomaly in anomalies] == ["voto"]


def test_collect_structural_anomalies_pools_across_documents_and_ignores_gold() -> None:
    predictions = [
        _region_prediction(
            "d1",
            gold=[(50, 60, "relatorio_fim"), (10, 20, "relatorio_inicio")],
            predicted=[(10, 20, "relatorio_inicio"), (50, 60, "relatorio_fim")],
        ),
        _region_prediction(
            "d2",
            gold=[],
            predicted=[(10, 20, "voto_fim"), (50, 60, "voto_inicio")],
        ),
    ]

    anomalies = collect_structural_anomalies(predictions)

    assert anomalies == [
        StructuralAnomaly(document_id="d2", base="voto", inicio=(50, 60), fim=(10, 20))
    ]


# #1052's "document-level structural diagnostics ... without pretending to
# prove semantic correctness" plus "save machine-readable metrics plus a
# human-readable error report with concrete examples" checklist items:
# region_eval already computes all of this, but nothing renders it into the
# same kind of human-readable report model_eval.render_error_report produces
# for span-level metrics.


def test_render_region_report_includes_per_region_type_metrics() -> None:
    predictions = [
        _region_prediction(
            "d1",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
    ]

    report = render_region_report(predictions)

    assert "relatorio" in report
    assert "match_rate=1.000" in report
    assert "mean_iou=1.000" in report


def test_render_region_report_reports_missed_region_without_iou() -> None:
    predictions = [
        _region_prediction("d1", [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")], []),
    ]

    report = render_region_report(predictions)

    assert "missed=1" in report
    assert "mean_iou=n/a" in report


def test_render_region_report_includes_structural_anomalies() -> None:
    predictions = [
        _region_prediction(
            "d1",
            [],
            [(80, 90, "relatorio_inicio"), (10, 20, "relatorio_fim")],
        ),
    ]

    report = render_region_report(predictions)

    assert "Structural anomalies (1 total)" in report
    assert "doc=d1" in report
    assert "base=relatorio" in report


def test_render_region_report_no_anomalies_reports_zero_count() -> None:
    predictions = [
        _region_prediction(
            "d1",
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
            [(0, 10, "relatorio_inicio"), (40, 50, "relatorio_fim")],
        ),
    ]

    report = render_region_report(predictions)

    assert "Structural anomalies (0 total)" in report
