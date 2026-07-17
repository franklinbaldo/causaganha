"""Inter-annotator agreement (RFC 0012 §8) — no PR #832 equivalent to reuse.

Implements the exact statistical spec RFC 0012 §8 fixes (after three review
rounds — the floor is normative, not release-configurable):

- **matching**: exact span match (``start``, ``end``, ``category``
  identical) between the two independent annotations of a document;
- **pooling**: per-category true/false positive/negative counts are pooled
  across every document in the split, not averaged per-document;
- **support**: a category's support is the size of the union of both
  annotators' spans for it (``tp + fp + fn``) — the number of distinct
  spans either annotator proposed;
- **aggregate gate**: macro-F1 over categories with support >= 5, gated on
  the **lower bound of a document-level bootstrap 95% CI** >= 0.75
  (fixed for ``segmenter-real-v8.1`` by RFC 0012 §5, not a release choice);
- **per-category gate**: floor 0.5, gated on the **lower CI bound** when a
  category has support >= 15, or on the **point estimate** when support is
  in [5, 15) — a CI is too wide to discriminate at n=5 (RFC 0012 §8, round
  3 review fix). Categories with support < 5 are reported but excluded
  from both the aggregate and the per-category gate (RFC 0012 §5.4).

IAA measures inter-annotator *reliability*, not validity against ground
truth (RFC 0012 §8's explicit epistemic limit) — passing this gate is
necessary but not sufficient for a release to call itself ``gold``; the
sufficient condition is the human-reference validation in RFC 0012 §9.1.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from segmenter_dataset.schemas import Label


AGGREGATE_FLOOR = 0.75
PER_CATEGORY_FLOOR = 0.5
MIN_REPORT_SUPPORT = 5
MIN_CI_GATE_SUPPORT = 15
DEFAULT_BOOTSTRAP_RESAMPLES = 1000


@dataclass(frozen=True)
class DocumentAnnotationPair:
    """Two independent annotations of the same document (RFC 0012 §5.3)."""

    document_id: str
    labels_a: tuple[Label, ...]
    labels_b: tuple[Label, ...]


def _span_set(labels: tuple[Label, ...], category: str) -> set[tuple[int, int]]:
    return {(label.start, label.end) for label in labels if label.category == category}


def _all_categories(pairs: list[DocumentAnnotationPair]) -> set[str]:
    categories: set[str] = set()
    for pair in pairs:
        categories.update(label.category for label in pair.labels_a)
        categories.update(label.category for label in pair.labels_b)
    return categories


def pooled_counts(pairs: list[DocumentAnnotationPair]) -> dict[str, tuple[int, int, int]]:
    """Pool exact-match ``(tp, fp, fn)`` per category across every pair in ``pairs``."""
    pooled: dict[str, list[int]] = {}
    for category in _all_categories(pairs):
        tp = fp = fn = 0
        for pair in pairs:
            spans_a = _span_set(pair.labels_a, category)
            spans_b = _span_set(pair.labels_b, category)
            tp += len(spans_a & spans_b)
            fp += len(spans_b - spans_a)
            fn += len(spans_a - spans_b)
        pooled[category] = [tp, fp, fn]
    return {category: (tp, fp, fn) for category, (tp, fp, fn) in pooled.items()}


def f1_from_counts(tp: int, fp: int, fn: int) -> float:
    """F1 from pooled counts; 0.0 when there is no support at all (denominator 0)."""
    denominator = 2 * tp + fp + fn
    return (2 * tp / denominator) if denominator > 0 else 0.0


def support(counts: tuple[int, int, int]) -> int:
    """RFC 0012 §8: support = size of the union of both annotators' spans."""
    tp, fp, fn = counts
    return tp + fp + fn


def per_category_f1(pairs: list[DocumentAnnotationPair]) -> dict[str, float]:
    """Pooled exact-match F1 per category across ``pairs``."""
    counts = pooled_counts(pairs)
    return {category: f1_from_counts(*c) for category, c in counts.items()}


def macro_f1(
    pairs: list[DocumentAnnotationPair], *, min_support: int = MIN_REPORT_SUPPORT
) -> float | None:
    """Macro-F1 over categories with support >= ``min_support``; ``None`` if none qualify."""
    counts = pooled_counts(pairs)
    f1s = [f1_from_counts(*c) for category, c in counts.items() if support(c) >= min_support]
    if not f1s:
        return None
    return sum(f1s) / len(f1s)


def _category_f1(pairs: list[DocumentAnnotationPair], category: str) -> float:
    counts = pooled_counts(pairs).get(category, (0, 0, 0))
    return f1_from_counts(*counts)


def bootstrap_ci_low(
    pairs: list[DocumentAnnotationPair],
    statistic: object,
    *,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int,
) -> float | None:
    """Lower bound of a 95% document-level bootstrap CI for ``statistic(pairs)``.

    Resamples **documents** with replacement (never spans directly), per
    RFC 0012 §8 — resampling spans would break the pooling structure
    within a document. ``statistic`` is any callable ``list[
    DocumentAnnotationPair] -> float | None``; returns ``None`` if the
    point statistic itself is undefined (e.g. zero qualifying support) for
    every resample.
    """
    rng = random.Random(seed)  # noqa: S311 - deterministic statistical resampling, not cryptography
    n = len(pairs)
    if n == 0:
        return None
    values: list[float] = []
    for _ in range(resamples):
        resample = [pairs[rng.randrange(n)] for _ in range(n)]
        value = statistic(resample)
        if value is not None:
            values.append(value)
    if not values:
        return None
    values.sort()
    low_index = int(0.025 * len(values))
    return values[low_index]


@dataclass(frozen=True)
class CategoryIaaResult:
    """Gate outcome for one trainable category."""

    category: str
    support: int
    point_estimate: float
    ci_low: float | None
    included_in_aggregate: bool
    passed_gate: bool
    gate_statistic: str  # "ci_lower_bound" | "point_estimate" | "not_gated_low_support"


@dataclass(frozen=True)
class IaaReport:
    """Full RFC 0012 §8 IAA report for one split (validation or test)."""

    macro_f1_point: float | None
    macro_f1_ci_low: float | None
    aggregate_passed: bool
    per_category: dict[str, CategoryIaaResult]
    unreliable_eval_categories: tuple[str, ...]


def compute_iaa_report(
    pairs: list[DocumentAnnotationPair],
    *,
    seed: int,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
) -> IaaReport:
    """Compute the full RFC 0012 §8 IAA report for one split's annotation pairs."""
    counts = pooled_counts(pairs)
    per_category: dict[str, CategoryIaaResult] = {}

    for category, category_counts in sorted(counts.items()):
        n_support = support(category_counts)
        point = f1_from_counts(*category_counts)

        if n_support < MIN_REPORT_SUPPORT:
            per_category[category] = CategoryIaaResult(
                category=category,
                support=n_support,
                point_estimate=point,
                ci_low=None,
                included_in_aggregate=False,
                passed_gate=False,
                gate_statistic="not_gated_low_support",
            )
            continue

        if n_support >= MIN_CI_GATE_SUPPORT:
            ci_low = bootstrap_ci_low(
                pairs,
                lambda sample, cat=category: _category_f1(sample, cat),
                resamples=resamples,
                seed=seed,
            )
            passed = ci_low is not None and ci_low >= PER_CATEGORY_FLOOR
            per_category[category] = CategoryIaaResult(
                category=category,
                support=n_support,
                point_estimate=point,
                ci_low=ci_low,
                included_in_aggregate=True,
                passed_gate=passed,
                gate_statistic="ci_lower_bound",
            )
        else:
            per_category[category] = CategoryIaaResult(
                category=category,
                support=n_support,
                point_estimate=point,
                ci_low=None,
                included_in_aggregate=True,
                passed_gate=point >= PER_CATEGORY_FLOOR,
                gate_statistic="point_estimate",
            )

    macro_point = macro_f1(pairs, min_support=MIN_REPORT_SUPPORT)
    macro_ci_low = bootstrap_ci_low(
        pairs,
        lambda sample: macro_f1(sample, min_support=MIN_REPORT_SUPPORT),
        resamples=resamples,
        seed=seed,
    )
    aggregate_passed = macro_ci_low is not None and macro_ci_low >= AGGREGATE_FLOOR

    unreliable = tuple(
        sorted(
            category
            for category, result in per_category.items()
            if result.included_in_aggregate and not result.passed_gate
        )
    )

    return IaaReport(
        macro_f1_point=macro_point,
        macro_f1_ci_low=macro_ci_low,
        aggregate_passed=aggregate_passed,
        per_category=per_category,
        unreliable_eval_categories=unreliable,
    )
