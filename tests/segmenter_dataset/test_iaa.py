from __future__ import annotations

import pytest

from segmenter_dataset.iaa import (
    AGGREGATE_FLOOR,
    MIN_CI_GATE_SUPPORT,
    PER_CATEGORY_FLOOR,
    DocumentAnnotationPair,
    compute_iaa_report,
    f1_from_counts,
    macro_f1,
    per_category_f1,
    pooled_counts,
    support,
)
from segmenter_dataset.schemas import Label


def _pair(
    doc_id: str, spans_a: list[tuple[int, int, str]], spans_b: list[tuple[int, int, str]]
) -> DocumentAnnotationPair:
    return DocumentAnnotationPair(
        document_id=doc_id,
        labels_a=tuple(Label(start=s, end=e, category=c) for s, e, c in spans_a),
        labels_b=tuple(Label(start=s, end=e, category=c) for s, e, c in spans_b),
    )


def test_f1_from_counts_perfect_agreement() -> None:
    assert f1_from_counts(tp=5, fp=0, fn=0) == 1.0


def test_f1_from_counts_no_overlap() -> None:
    assert f1_from_counts(tp=0, fp=3, fn=3) == 0.0


def test_f1_from_counts_zero_support_is_zero_not_nan() -> None:
    assert f1_from_counts(tp=0, fp=0, fn=0) == 0.0


def test_pooled_counts_perfect_agreement_across_documents() -> None:
    pairs = [
        _pair("d1", [(0, 5, "cat")], [(0, 5, "cat")]),
        _pair("d2", [(0, 5, "cat")], [(0, 5, "cat")]),
    ]
    counts = pooled_counts(pairs)
    assert counts["cat"] == (2, 0, 0)
    assert support(counts["cat"]) == 2


def test_per_category_f1_disagreement() -> None:
    pairs = [_pair("d1", [(0, 5, "cat")], [(10, 15, "cat")])]
    f1s = per_category_f1(pairs)
    assert f1s["cat"] == 0.0


def test_macro_f1_excludes_low_support_categories() -> None:
    pairs = [_pair("d1", [(0, 5, "rare")], [(0, 5, "rare")])]
    assert macro_f1(pairs, min_support=5) is None


def test_macro_f1_includes_categories_meeting_support() -> None:
    pairs = [_pair(f"d{i}", [(0, 5, "cat")], [(0, 5, "cat")]) for i in range(5)]
    assert macro_f1(pairs, min_support=5) == 1.0


def test_compute_iaa_report_perfect_agreement_passes_aggregate_gate() -> None:
    pairs = [_pair(f"d{i}", [(0, 5, "cat")], [(0, 5, "cat")]) for i in range(30)]
    report = compute_iaa_report(pairs, seed=1, resamples=200)
    assert report.macro_f1_point == 1.0
    assert report.macro_f1_ci_low is not None
    assert report.macro_f1_ci_low >= AGGREGATE_FLOOR
    assert report.aggregate_passed is True
    assert report.unreliable_eval_categories == ()


def test_compute_iaa_report_total_disagreement_fails_gate() -> None:
    pairs = [_pair(f"d{i}", [(0, 5, "cat")], [(10, 15, "cat")]) for i in range(30)]
    report = compute_iaa_report(pairs, seed=1, resamples=200)
    assert report.aggregate_passed is False
    assert "cat" in report.unreliable_eval_categories


def test_compute_iaa_report_low_support_category_not_gated_by_ci() -> None:
    # Support of 5 (< MIN_CI_GATE_SUPPORT=15) -> point-estimate gate, not CI.
    pairs = [_pair(f"d{i}", [(0, 5, "cat")], [(0, 5, "cat")]) for i in range(5)]
    report = compute_iaa_report(pairs, seed=1, resamples=200)
    result = report.per_category["cat"]
    assert result.support == 5
    assert result.gate_statistic == "point_estimate"
    assert result.point_estimate >= PER_CATEGORY_FLOOR
    assert result.passed_gate is True


def test_compute_iaa_report_very_low_support_not_gated_at_all() -> None:
    pairs = [_pair("d1", [(0, 5, "cat")], [(0, 5, "cat")])]
    report = compute_iaa_report(pairs, seed=1, resamples=50)
    result = report.per_category["cat"]
    assert result.support == 1
    assert result.gate_statistic == "not_gated_low_support"
    assert result.included_in_aggregate is False


def test_compute_iaa_report_heterogeneous_agreement_bootstrap_varies() -> None:
    """Distinguishes a correct bootstrap from one that just returns the point estimate.

    Every other IAA test in this module uses homogeneous data (all-agree or
    all-disagree documents), where every resample reproduces the same
    per-category counts as the full sample — a bootstrap implementation
    that (incorrectly) always returned the point estimate unchanged would
    pass those tests too. Mixing 20 perfectly-agreeing documents with 10
    perfectly-disagreeing ones makes the resampled composition (and hence
    the resampled F1) genuinely vary run to run, so ``macro_f1_ci_low``
    landing strictly below the point estimate is only possible if resampling
    is actually happening.
    """
    agree = [_pair(f"agree{i}", [(0, 5, "cat")], [(0, 5, "cat")]) for i in range(20)]
    disagree = [_pair(f"dis{i}", [(0, 5, "cat")], [(10, 15, "cat")]) for i in range(10)]
    pairs = agree + disagree

    report = compute_iaa_report(pairs, seed=1, resamples=1000)
    result = report.per_category["cat"]

    assert result.support == 40
    assert result.point_estimate == pytest.approx(2 / 3)
    assert result.ci_low is not None
    # A buggy "bootstrap" that just re-reports the point estimate every
    # resample would make ci_low == point_estimate exactly; a real one
    # produces a lower tail from unlucky resamples that draw more
    # disagreement.
    assert result.ci_low < result.point_estimate
    assert report.macro_f1_ci_low is not None
    assert report.macro_f1_ci_low < report.macro_f1_point


def test_compute_iaa_report_support_exactly_15_uses_ci_gate() -> None:
    """Boundary test at MIN_CI_GATE_SUPPORT (15) — only 1 and 5 were covered before.

    Support of exactly 15 must take the CI-lower-bound gate path (the ``>=``
    in ``compute_iaa_report``'s branch), not the point-estimate path used
    for support in [5, 15).
    """
    pairs = [_pair(f"d{i}", [(0, 5, "cat")], [(0, 5, "cat")]) for i in range(MIN_CI_GATE_SUPPORT)]
    report = compute_iaa_report(pairs, seed=1, resamples=200)
    result = report.per_category["cat"]
    assert result.support == MIN_CI_GATE_SUPPORT
    assert result.gate_statistic == "ci_lower_bound"
    assert result.ci_low is not None


def test_compute_iaa_report_support_one_below_boundary_uses_point_estimate_gate() -> None:
    """One below the MIN_CI_GATE_SUPPORT boundary — contrasts with support == 15."""
    pairs = [
        _pair(f"d{i}", [(0, 5, "cat")], [(0, 5, "cat")]) for i in range(MIN_CI_GATE_SUPPORT - 1)
    ]
    report = compute_iaa_report(pairs, seed=1, resamples=200)
    result = report.per_category["cat"]
    assert result.support == MIN_CI_GATE_SUPPORT - 1
    assert result.gate_statistic == "point_estimate"
