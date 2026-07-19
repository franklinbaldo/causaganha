from __future__ import annotations

from segmenter_dataset.model_eval import (
    DocumentModelPrediction,
    bootstrap_diff_ci_low,
    critical_category_f1,
    evaluate_model_acceptance,
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
