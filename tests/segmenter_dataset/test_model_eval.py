from __future__ import annotations

import pytest

from segmenter_dataset.model_eval import (
    CategoryMetrics,
    DocumentModelPrediction,
    MicroMetrics,
    SpanErrorBreakdown,
    SpanErrorExample,
    bootstrap_diff_ci_low,
    classify_span_errors,
    collect_span_error_examples,
    critical_category_f1,
    evaluate_model_acceptance,
    micro_metrics,
    per_category_metrics,
    render_error_report,
    trivial_baseline_predictions,
)
from segmenter_dataset.ontology import CRITICAL_CATEGORIES
from segmenter_dataset.schemas import Label


def _labels(spans: list[tuple[int, int, str]]) -> tuple[Label, ...]:
    return tuple(Label(start=s, end=e, category=c) for s, e, c in spans)


def _prediction(
    doc_id: str,
    gold: list[tuple[int, int, str]],
    model_predicted: list[tuple[int, int, str]],
    baseline_predicted: list[tuple[int, int, str]] | None = None,
) -> DocumentModelPrediction:
    return DocumentModelPrediction(
        document_id=doc_id,
        gold=_labels(gold),
        model_predicted=_labels(model_predicted),
        baseline_predicted=_labels(baseline_predicted or []),
    )


def _perfect_predictions(n: int, category: str = "resultado") -> list[DocumentModelPrediction]:
    return [_prediction(f"d{i}", [(0, 5, category)], [(0, 5, category)]) for i in range(n)]


def test_trivial_baseline_predicts_no_spans() -> None:
    gold_by_document = {"d1": _labels([(0, 5, "resultado")])}
    predictions = trivial_baseline_predictions(["d1"], gold_by_document)

    assert predictions[0].baseline_predicted == ()
    assert predictions[0].model_predicted == ()
    assert predictions[0].gold == gold_by_document["d1"]


def test_bootstrap_diff_ci_low_empty_predictions_is_none() -> None:
    assert bootstrap_diff_ci_low([], resamples=10, seed=1) is None


def test_bootstrap_diff_ci_low_positive_when_model_perfect_and_baseline_empty() -> None:
    predictions = [
        _prediction("d1", [(0, 5, "resultado")], [(0, 5, "resultado")], baseline_predicted=[]),
        _prediction("d2", [(0, 5, "resultado")], [(0, 5, "resultado")], baseline_predicted=[]),
        _prediction("d3", [(0, 5, "resultado")], [(0, 5, "resultado")], baseline_predicted=[]),
        _prediction("d4", [(0, 5, "resultado")], [(0, 5, "resultado")], baseline_predicted=[]),
        _prediction("d5", [(0, 5, "resultado")], [(0, 5, "resultado")], baseline_predicted=[]),
    ]

    ci_low = bootstrap_diff_ci_low(predictions, resamples=200, seed=7, min_support=1)

    assert ci_low is not None
    assert ci_low > 0


def test_bootstrap_diff_ci_low_zero_when_model_equals_baseline() -> None:
    predictions = [
        _prediction("d1", [(0, 5, "resultado")], [(0, 5, "resultado")], [(0, 5, "resultado")]),
        _prediction("d2", [(0, 5, "resultado")], [(0, 5, "resultado")], [(0, 5, "resultado")]),
    ]

    ci_low = bootstrap_diff_ci_low(predictions, resamples=50, seed=3, min_support=1)

    assert ci_low == 0.0


def test_critical_category_f1_covers_every_fixed_category_even_with_zero_support() -> None:
    predictions = [_prediction("d1", [(0, 5, "resultado")], [(0, 5, "resultado")])]

    per_category = critical_category_f1(predictions)

    assert set(per_category) == set(CRITICAL_CATEGORIES)
    assert per_category["resultado"] == 1.0
    assert per_category["dispositivo_abertura"] == 0.0


def test_per_category_metrics_reports_every_category_from_gold_or_prediction() -> None:
    predictions = [
        _prediction("d1", [(0, 5, "resultado")], [(0, 5, "resultado")]),
        _prediction("d2", [(0, 5, "dispositivo_abertura")], []),
        _prediction("d3", [], [(20, 25, "extra")]),
    ]

    metrics = per_category_metrics(predictions)

    assert set(metrics) == {"resultado", "dispositivo_abertura", "extra"}
    assert metrics["resultado"] == CategoryMetrics(
        category="resultado", support=1, tp=1, fp=0, fn=0, precision=1.0, recall=1.0, f1=1.0
    )
    assert metrics["dispositivo_abertura"] == CategoryMetrics(
        category="dispositivo_abertura",
        support=1,
        tp=0,
        fp=0,
        fn=1,
        precision=0.0,
        recall=0.0,
        f1=0.0,
    )
    assert metrics["extra"] == CategoryMetrics(
        category="extra", support=1, tp=0, fp=1, fn=0, precision=0.0, recall=0.0, f1=0.0
    )


def test_per_category_metrics_omits_categories_with_no_gold_or_prediction() -> None:
    predictions = [_prediction("d1", [(0, 5, "resultado")], [(0, 5, "resultado")])]

    metrics = per_category_metrics(predictions)

    assert "dispositivo_abertura" not in metrics


def test_per_category_metrics_pools_counts_across_documents() -> None:
    predictions = [
        _prediction("d1", [(0, 5, "resultado")], [(0, 5, "resultado")]),
        _prediction("d2", [(0, 5, "resultado")], []),
        _prediction("d3", [], [(10, 15, "resultado")]),
    ]

    metrics = per_category_metrics(predictions)

    assert metrics["resultado"].tp == 1
    assert metrics["resultado"].fn == 1
    assert metrics["resultado"].fp == 1
    assert metrics["resultado"].support == 3
    assert metrics["resultado"].precision == pytest.approx(0.5)
    assert metrics["resultado"].recall == pytest.approx(0.5)


def test_micro_metrics_pools_counts_across_categories_instead_of_averaging_per_category() -> None:
    # Category "a" is perfect (f1=1.0) but has one document; category "b" is
    # all misses (f1=0.0) across three documents. Macro-F1 weighs both
    # categories equally (mean(1.0, 0.0) = 0.5); micro pools raw counts, so
    # the more frequent, worse-performing category dominates the result.
    predictions = [
        _prediction("d1", [(0, 5, "a")], [(0, 5, "a")]),
        _prediction("d2", [(0, 5, "b")], []),
        _prediction("d3", [(0, 5, "b")], []),
        _prediction("d4", [(0, 5, "b")], []),
    ]

    metrics = micro_metrics(predictions)

    assert metrics == MicroMetrics(
        tp=1, fp=0, fn=3, precision=1.0, recall=0.25, f1=pytest.approx(0.4)
    )


def test_micro_metrics_perfect_predictions_is_one() -> None:
    predictions = _perfect_predictions(3)

    metrics = micro_metrics(predictions)

    assert metrics.precision == 1.0
    assert metrics.recall == 1.0
    assert metrics.f1 == 1.0


def test_micro_metrics_no_gold_or_predicted_spans_is_zero() -> None:
    predictions = [_prediction("d1", [], [])]

    metrics = micro_metrics(predictions)

    assert metrics == MicroMetrics(tp=0, fp=0, fn=0, precision=0.0, recall=0.0, f1=0.0)


def test_evaluate_model_acceptance_reports_micro_metrics_as_secondary_context() -> None:
    predictions = [
        _prediction("d1", [(0, 5, "a")], [(0, 5, "a")]),
        _prediction("d2", [(0, 5, "b")], []),
        _prediction("d3", [(0, 5, "b")], []),
        _prediction("d4", [(0, 5, "b")], []),
    ]

    report = evaluate_model_acceptance(predictions, seed=1, resamples=10, min_support=1)

    assert report.micro_f1_model == pytest.approx(0.4)
    assert report.micro_precision_model == 1.0
    assert report.micro_recall_model == 0.25


def test_evaluate_model_acceptance_passes_when_model_beats_baseline_and_clears_floor() -> None:
    predictions = []
    for category in sorted(CRITICAL_CATEGORIES):
        predictions.extend(_perfect_predictions(6, category=category))

    report = evaluate_model_acceptance(predictions, seed=1, resamples=200, min_support=1)

    assert report.beats_baseline is True
    assert report.critical_categories_passed is True
    assert report.eligible_for_deploy is True
    assert report.macro_f1_model == 1.0
    assert report.macro_f1_baseline == 0.0


def test_evaluate_model_acceptance_fails_critical_floor_when_model_misses_spans() -> None:
    predictions = [_prediction(f"d{i}", [(0, 5, "resultado")], []) for i in range(6)]

    report = evaluate_model_acceptance(predictions, seed=1, resamples=100, min_support=1)

    assert report.critical_categories_passed is False
    assert report.eligible_for_deploy is False


def test_classify_span_errors_exact_match_has_no_errors() -> None:
    predictions = [_prediction("d1", [(0, 10, "resultado")], [(0, 10, "resultado")])]

    breakdown = classify_span_errors(predictions)

    assert breakdown == SpanErrorBreakdown(
        category_errors=0, boundary_errors=0, pure_misses=0, pure_extras=0
    )


def test_classify_span_errors_overlap_same_category_is_boundary_error() -> None:
    predictions = [_prediction("d1", [(0, 10, "resultado")], [(0, 8, "resultado")])]

    breakdown = classify_span_errors(predictions)

    assert breakdown == SpanErrorBreakdown(
        category_errors=0, boundary_errors=1, pure_misses=0, pure_extras=0
    )


def test_classify_span_errors_same_offsets_different_category_is_category_error() -> None:
    predictions = [_prediction("d1", [(0, 10, "resultado")], [(0, 10, "dispositivo_abertura")])]

    breakdown = classify_span_errors(predictions)

    assert breakdown == SpanErrorBreakdown(
        category_errors=1, boundary_errors=0, pure_misses=0, pure_extras=0
    )


def test_classify_span_errors_overlap_different_category_is_category_error_not_boundary() -> None:
    predictions = [_prediction("d1", [(0, 10, "resultado")], [(2, 12, "dispositivo_abertura")])]

    breakdown = classify_span_errors(predictions)

    assert breakdown == SpanErrorBreakdown(
        category_errors=1, boundary_errors=0, pure_misses=0, pure_extras=0
    )


def test_classify_span_errors_no_overlap_is_pure_miss_and_pure_extra() -> None:
    predictions = [_prediction("d1", [(0, 10, "resultado")], [(50, 60, "resultado")])]

    breakdown = classify_span_errors(predictions)

    assert breakdown == SpanErrorBreakdown(
        category_errors=0, boundary_errors=0, pure_misses=1, pure_extras=1
    )


def test_classify_span_errors_pools_counts_across_documents() -> None:
    predictions = [
        _prediction("d1", [(0, 10, "resultado")], [(0, 10, "resultado")]),
        _prediction("d2", [(0, 10, "resultado")], [(0, 8, "resultado")]),
        _prediction("d3", [(0, 10, "resultado")], [(0, 10, "dispositivo_abertura")]),
        _prediction("d4", [(0, 10, "resultado")], [(50, 60, "resultado")]),
    ]

    breakdown = classify_span_errors(predictions)

    assert breakdown == SpanErrorBreakdown(
        category_errors=1, boundary_errors=1, pure_misses=1, pure_extras=1
    )


def test_classify_span_errors_matches_the_best_overlapping_candidate() -> None:
    # Gold [0, 10) overlaps two unmatched predictions; the closer one, [0, 9),
    # has more overlap than [5, 20) and must be picked, leaving [5, 20) as a
    # pure extra rather than double-counting a boundary error.
    predictions = [
        _prediction(
            "d1",
            [(0, 10, "resultado")],
            [(0, 9, "resultado"), (5, 20, "resultado")],
        )
    ]

    breakdown = classify_span_errors(predictions)

    assert breakdown == SpanErrorBreakdown(
        category_errors=0, boundary_errors=1, pure_misses=0, pure_extras=1
    )


def test_collect_span_error_examples_excludes_exact_matches() -> None:
    predictions = [_prediction("d1", [(0, 10, "resultado")], [(0, 10, "resultado")])]

    assert collect_span_error_examples(predictions) == []


def test_collect_span_error_examples_covers_every_error_type() -> None:
    predictions = [
        _prediction("d1", [(0, 10, "resultado")], [(0, 8, "resultado")]),  # boundary
        _prediction("d2", [(0, 10, "resultado")], [(0, 10, "dispositivo_abertura")]),  # category
        _prediction("d3", [(0, 10, "resultado")], []),  # pure miss
        _prediction("d4", [], [(50, 60, "resultado")]),  # pure extra
    ]

    examples = collect_span_error_examples(predictions)

    assert set(example.error_type for example in examples) == {
        "boundary_error",
        "category_error",
        "pure_miss",
        "pure_extra",
    }
    boundary = next(e for e in examples if e.error_type == "boundary_error")
    assert boundary == SpanErrorExample(
        document_id="d1",
        error_type="boundary_error",
        gold=Label(start=0, end=10, category="resultado"),
        predicted=Label(start=0, end=8, category="resultado"),
    )
    miss = next(e for e in examples if e.error_type == "pure_miss")
    assert miss.document_id == "d3"
    assert miss.gold == Label(start=0, end=10, category="resultado")
    assert miss.predicted is None
    extra = next(e for e in examples if e.error_type == "pure_extra")
    assert extra.document_id == "d4"
    assert extra.gold is None
    assert extra.predicted == Label(start=50, end=60, category="resultado")


def test_collect_span_error_examples_caps_examples_per_type() -> None:
    predictions = [_prediction(f"d{i}", [(0, 10, "resultado")], []) for i in range(10)]

    examples = collect_span_error_examples(predictions, limit_per_type=3)

    assert len(examples) == 3
    assert all(example.error_type == "pure_miss" for example in examples)


def test_render_error_report_includes_per_category_metrics() -> None:
    predictions = [_prediction("d1", [(0, 5, "resultado")], [(0, 5, "resultado")])]

    report = render_error_report(predictions)

    assert "resultado" in report
    assert "precision=1.000" in report
    assert "recall=1.000" in report


def test_render_error_report_includes_error_breakdown_counts() -> None:
    predictions = [_prediction("d1", [(0, 10, "resultado")], [(0, 8, "resultado")])]

    report = render_error_report(predictions)

    assert "boundary_errors: 1" in report
    assert "category_errors: 0" in report
    assert "pure_misses: 0" in report
    assert "pure_extras: 0" in report


def test_render_error_report_includes_concrete_examples() -> None:
    predictions = [_prediction("d1", [(0, 10, "resultado")], [(0, 8, "resultado")])]

    report = render_error_report(predictions)

    assert "doc=d1" in report
    assert "resultado[0:10]" in report
    assert "resultado[0:8]" in report


def test_render_error_report_respects_max_examples_per_type() -> None:
    predictions = [_prediction(f"d{i}", [(0, 10, "resultado")], []) for i in range(10)]

    report = render_error_report(predictions, max_examples_per_type=2)

    assert report.count("pure_miss") == 3  # heading count "pure_misses: 10" + 2 example lines
