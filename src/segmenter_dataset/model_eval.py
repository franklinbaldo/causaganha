"""Test-set model-release acceptance gate (RFC 0012 §16.2 / §5 point 6).

Passing the dataset gates (§16.1, ``release.py``) says the *data* is
trustworthy; it says nothing about whether a checkpoint trained on it is
worth deploying — a perfectly reproducible model with near-zero test F1
clears every §16.1 gate and is still useless. §16.2 fixes two additional,
non-waivable checks against the single, locked test evaluation:

- **beats a trivial baseline**: the lower bound of a document-level
  bootstrap 95% CI of macro-F1(model) minus macro-F1(baseline) must be
  strictly greater than 0 — not a margin the release picks after seeing the
  result;
- **critical-category floor**: ``ontology.CRITICAL_CATEGORIES`` — the
  categories carrying the decision's operative outcome — must each clear
  ``ontology.CRITICAL_CATEGORY_FLOOR`` macro-F1 as a **point estimate** (not
  a CI bound; test-set support for these categories is too low at ~30
  documents for a CI to discriminate, the same reasoning IAA's per-category
  gate uses at low support, §8).

The statistics reuse :mod:`segmenter_dataset.iaa`'s pooled exact-match F1
machinery: a (gold, model-prediction) pair is structurally the same thing as
an IAA (annotator-A, annotator-B) pair, so ``DocumentAnnotationPair``,
``pooled_counts``, ``f1_from_counts``, and ``macro_f1`` all apply unchanged.
Only the *paired* baseline-vs-model bootstrap is new here — it must resample
the same document indices for both predictors in the same draw, or it
overstates the CI width by ignoring that both predictors' errors are
correlated within a document.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from segmenter_dataset.iaa import (
    MIN_REPORT_SUPPORT,
    DocumentAnnotationPair,
    f1_from_counts,
    macro_f1,
    pooled_counts,
    precision_from_counts,
    recall_from_counts,
    support,
)
from segmenter_dataset.ontology import CRITICAL_CATEGORIES, CRITICAL_CATEGORY_FLOOR
from segmenter_dataset.schemas import ModelAcceptanceEvidence


if TYPE_CHECKING:
    from segmenter_dataset.schemas import Label


DEFAULT_BOOTSTRAP_RESAMPLES = 1000


@dataclass(frozen=True)
class DocumentModelPrediction:
    """One test document's gold labels plus model and trivial-baseline predictions."""

    document_id: str
    gold: tuple[Label, ...]
    model_predicted: tuple[Label, ...]
    baseline_predicted: tuple[Label, ...]

    @property
    def model_pair(self) -> DocumentAnnotationPair:
        """Gold-vs-model as an IAA-shaped pair, for reusing ``iaa``'s pooled F1."""
        return DocumentAnnotationPair(self.document_id, self.gold, self.model_predicted)

    @property
    def baseline_pair(self) -> DocumentAnnotationPair:
        """Gold-vs-baseline as an IAA-shaped pair, for reusing ``iaa``'s pooled F1."""
        return DocumentAnnotationPair(self.document_id, self.gold, self.baseline_predicted)


def trivial_baseline_predictions(
    document_ids: list[str], gold_by_document: dict[str, tuple[Label, ...]]
) -> list[DocumentModelPrediction]:
    """RFC 0012 §5 point 6's fallback baseline: majority-class, i.e. predict no spans.

    Used "na ausência de" an existing heuristic/deterministic extractor. In
    BIOES span tagging the majority class is overwhelmingly ``O`` (outside
    any span), so the majority-class predictor never emits a span — every
    category scores F1=0 against it, which is what makes "beats baseline"
    a meaningful bar rather than a rubber stamp: it only asks that the model
    reliably finds real spans, not that it beats a strong competitor.
    """
    return [
        DocumentModelPrediction(
            document_id=document_id,
            gold=gold_by_document[document_id],
            model_predicted=(),
            baseline_predicted=(),
        )
        for document_id in document_ids
    ]


def bootstrap_diff_ci_low(
    predictions: list[DocumentModelPrediction],
    *,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int,
    min_support: int = MIN_REPORT_SUPPORT,
) -> float | None:
    """Lower 95% CI bound of macro-F1(model) minus macro-F1(baseline), paired per document.

    Resamples document indices once per draw and applies the **same**
    indices to both the model pair list and the baseline pair list, so the
    within-document correlation between the two predictors' errors is
    preserved (an unpaired bootstrap — resampling each side independently —
    would overstate the CI width). Mirrors ``iaa.bootstrap_ci_low``'s
    document-level resampling discipline (RFC 0012 §8).
    """
    rng = random.Random(seed)  # noqa: S311 - deterministic statistical resampling, not cryptography
    n = len(predictions)
    if n == 0:
        return None
    diffs: list[float] = []
    for _ in range(resamples):
        sample = [predictions[rng.randrange(n)] for _ in range(n)]
        model_f1 = macro_f1([item.model_pair for item in sample], min_support=min_support)
        baseline_f1 = macro_f1([item.baseline_pair for item in sample], min_support=min_support)
        if model_f1 is not None and baseline_f1 is not None:
            diffs.append(model_f1 - baseline_f1)
    if not diffs:
        return None
    diffs.sort()
    low_index = int(0.025 * len(diffs))
    return diffs[low_index]


@dataclass(frozen=True)
class CategoryMetrics:
    """Full gold-vs-model breakdown for one category (#1052's span-metrics harness).

    Every category with any gold or predicted span appears when produced by
    :func:`per_category_metrics` — unlike ``iaa.macro_f1``'s reliability-gated
    aggregate (RFC 0012 §8's ``min_support`` floor), a rare category's zero
    recall must stay visible here rather than being silently dropped.
    """

    category: str
    support: int
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float


def per_category_metrics(predictions: list[DocumentModelPrediction]) -> dict[str, CategoryMetrics]:
    """Support/TP/FP/FN/precision/recall/F1 per category, pooled gold vs model.

    Reuses ``iaa.pooled_counts``' exact-match counting (gold as ``labels_a``,
    model prediction as ``labels_b``, per ``DocumentModelPrediction.model_pair``),
    so ``fp`` means "predicted but not gold" and ``fn`` means "gold but not
    predicted" — the standard precision/recall direction.
    """
    pairs = [item.model_pair for item in predictions]
    counts = pooled_counts(pairs)
    return {
        category: CategoryMetrics(
            category=category,
            support=support(c),
            tp=c[0],
            fp=c[1],
            fn=c[2],
            precision=precision_from_counts(*c),
            recall=recall_from_counts(*c),
            f1=f1_from_counts(*c),
        )
        for category, c in sorted(counts.items())
    }


@dataclass(frozen=True)
class MicroMetrics:
    """Global pooled precision/recall/F1 across every category (#1052's micro-metrics context).

    Unlike macro-F1 (mean of per-category F1, equal weight per category
    regardless of frequency), micro pools TP/FP/FN across *all* categories
    before computing one precision/recall/F1 — so a frequent,
    badly-performing category dominates the number instead of being
    averaged away by a well-scoring rare one. Reported as secondary
    context only: RFC 0012's beats-baseline/critical-floor gates stay
    macro-based (``evaluate_model_acceptance``).
    """

    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float


def micro_metrics(predictions: list[DocumentModelPrediction]) -> MicroMetrics:
    """Pool TP/FP/FN across every category (gold vs model) into one precision/recall/F1."""
    pairs = [item.model_pair for item in predictions]
    counts = pooled_counts(pairs)
    tp = sum(c[0] for c in counts.values())
    fp = sum(c[1] for c in counts.values())
    fn = sum(c[2] for c in counts.values())
    return MicroMetrics(
        tp=tp,
        fp=fp,
        fn=fn,
        precision=precision_from_counts(tp, fp, fn),
        recall=recall_from_counts(tp, fp, fn),
        f1=f1_from_counts(tp, fp, fn),
    )


def critical_category_f1(predictions: list[DocumentModelPrediction]) -> dict[str, float]:
    """Point-estimate pooled F1 (model vs. gold) for each RFC-fixed critical category."""
    pairs = [item.model_pair for item in predictions]
    counts = pooled_counts(pairs)
    return {
        category: f1_from_counts(*counts.get(category, (0, 0, 0)))
        for category in sorted(CRITICAL_CATEGORIES)
    }


@dataclass(frozen=True)
class SpanErrorBreakdown:
    """Error taxonomy for non-exact-match spans (#1052's anchor-metrics diagnostic).

    Every gold or predicted span that is not an exact ``(start, end,
    category)`` match falls into exactly one bucket:

    - ``category_errors``: predicted and gold spans overlap but disagree on
      category — the model found the right location, wrong label.
    - ``boundary_errors``: predicted and gold spans overlap and agree on
      category, but offsets differ — right label, imprecise boundaries.
    - ``pure_misses``: a gold span with no overlapping prediction at all.
    - ``pure_extras``: a predicted span with no overlapping gold at all.
    """

    category_errors: int
    boundary_errors: int
    pure_misses: int
    pure_extras: int


def _spans_overlap(a: Label, b: Label) -> bool:
    return a.start < b.end and b.start < a.end


def _overlap_length(a: Label, b: Label) -> int:
    return min(a.end, b.end) - max(a.start, b.start)


@dataclass(frozen=True)
class SpanErrorExample:
    """One concrete gold/predicted span pair illustrating one ``SpanErrorBreakdown`` bucket.

    ``gold``/``predicted`` follow the same per-type shape ``classify_span_errors``
    counts: both set for ``category_error``/``boundary_error`` (the overlapping
    pair), only ``gold`` set for ``pure_miss``, only ``predicted`` set for
    ``pure_extra``. Feeds ``render_error_report``'s "why did the metric move"
    narrative (#1052's human-readable error report).
    """

    document_id: str
    error_type: str
    gold: Label | None
    predicted: Label | None


def _match_document_spans(
    document_id: str, gold: tuple[Label, ...], predicted: tuple[Label, ...]
) -> list[SpanErrorExample]:
    """Classify one document's non-exact-match spans into concrete ``SpanErrorExample``s.

    Same overlap-matching logic ``classify_span_errors`` pools into counts,
    but keeps the actual ``Label``s so callers can show *which* spans caused
    each error instead of only how many.
    """
    exact_matches = set(gold) & set(predicted)
    gold_remaining = [label for label in gold if label not in exact_matches]
    predicted_remaining = [label for label in predicted if label not in exact_matches]

    examples: list[SpanErrorExample] = []
    matched_gold_indices: set[int] = set()
    matched_predicted_indices: set[int] = set()

    sorted_gold_indices = sorted(
        range(len(gold_remaining)),
        key=lambda index: (gold_remaining[index].start, gold_remaining[index].end),
    )
    for gold_index in sorted_gold_indices:
        gold_label = gold_remaining[gold_index]
        candidates = [
            (index, predicted_label)
            for index, predicted_label in enumerate(predicted_remaining)
            if index not in matched_predicted_indices
            and _spans_overlap(gold_label, predicted_label)
        ]
        if not candidates:
            continue
        best_index, best_predicted = max(
            candidates,
            key=lambda item: (_overlap_length(gold_label, item[1]), -item[1].start),
        )
        matched_predicted_indices.add(best_index)
        matched_gold_indices.add(gold_index)
        error_type = (
            "boundary_error" if best_predicted.category == gold_label.category else "category_error"
        )
        examples.append(SpanErrorExample(document_id, error_type, gold_label, best_predicted))

    for gold_index, gold_label in enumerate(gold_remaining):
        if gold_index not in matched_gold_indices:
            examples.append(SpanErrorExample(document_id, "pure_miss", gold_label, None))
    for predicted_index, predicted_label in enumerate(predicted_remaining):
        if predicted_index not in matched_predicted_indices:
            examples.append(SpanErrorExample(document_id, "pure_extra", None, predicted_label))

    return examples


def classify_span_errors(predictions: list[DocumentModelPrediction]) -> SpanErrorBreakdown:
    """Pool ``SpanErrorBreakdown`` counts (gold vs model) across every document."""
    category_errors = boundary_errors = pure_misses = pure_extras = 0
    for item in predictions:
        for example in _match_document_spans(item.document_id, item.gold, item.model_predicted):
            if example.error_type == "category_error":
                category_errors += 1
            elif example.error_type == "boundary_error":
                boundary_errors += 1
            elif example.error_type == "pure_miss":
                pure_misses += 1
            else:
                pure_extras += 1
    return SpanErrorBreakdown(
        category_errors=category_errors,
        boundary_errors=boundary_errors,
        pure_misses=pure_misses,
        pure_extras=pure_extras,
    )


def collect_span_error_examples(
    predictions: list[DocumentModelPrediction], *, limit_per_type: int = 5
) -> list[SpanErrorExample]:
    """Concrete gold/predicted span examples for each error type, capped per type.

    Walks ``predictions`` in order and stops collecting a given
    ``error_type`` once ``limit_per_type`` examples exist for it, so a
    report over a large test set stays readable instead of listing every
    single miss.
    """
    counts: dict[str, int] = {}
    collected: list[SpanErrorExample] = []
    for item in predictions:
        for example in _match_document_spans(item.document_id, item.gold, item.model_predicted):
            if counts.get(example.error_type, 0) >= limit_per_type:
                continue
            counts[example.error_type] = counts.get(example.error_type, 0) + 1
            collected.append(example)
    return collected


def _format_label(label: Label | None) -> str:
    if label is None:
        return "-"
    return f"{label.category}[{label.start}:{label.end}]"


def render_error_report(
    predictions: list[DocumentModelPrediction],
    *,
    max_examples_per_type: int = 3,
) -> str:
    """Human-readable span error report: per-category metrics plus concrete examples (#1052).

    Complements the machine-readable metrics (``CategoryMetrics``,
    ``MicroMetrics``, ``ModelAcceptanceEvidence``) rather than replacing
    them — the goal is to explain *why* a number moved, not to recompute it
    differently.
    """
    lines = [f"# Span error report ({len(predictions)} documents)", "", "## Per-category metrics"]
    for category, metrics in per_category_metrics(predictions).items():
        lines.append(
            f"- {category}: support={metrics.support} precision={metrics.precision:.3f} "
            f"recall={metrics.recall:.3f} f1={metrics.f1:.3f}"
        )

    breakdown = classify_span_errors(predictions)
    lines.extend(
        [
            "",
            "## Error breakdown",
            f"- category_errors: {breakdown.category_errors}",
            f"- boundary_errors: {breakdown.boundary_errors}",
            f"- pure_misses: {breakdown.pure_misses}",
            f"- pure_extras: {breakdown.pure_extras}",
            "",
            "## Concrete examples",
        ]
    )
    for example in collect_span_error_examples(predictions, limit_per_type=max_examples_per_type):
        lines.append(
            f"- [{example.error_type}] doc={example.document_id} "
            f"gold={_format_label(example.gold)} predicted={_format_label(example.predicted)}"
        )

    return "\n".join(lines)


def evaluate_model_acceptance(
    predictions: list[DocumentModelPrediction],
    *,
    seed: int,
    resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    min_support: int = MIN_REPORT_SUPPORT,
) -> ModelAcceptanceEvidence:
    """Run the full RFC 0012 §16.2 gate against one locked test evaluation.

    Call this exactly once per test unlock (RFC 0012 §13.1/§13.2) — the
    function itself is pure and re-runnable, but the *evaluation it
    describes* is not: a second call against the same test predictions is a
    diagnostic re-check, never a new performance claim.
    """
    model_pairs = [item.model_pair for item in predictions]
    baseline_pairs = [item.baseline_pair for item in predictions]
    macro_model = macro_f1(model_pairs, min_support=min_support)
    macro_baseline = macro_f1(baseline_pairs, min_support=min_support)
    diff_ci_low = bootstrap_diff_ci_low(
        predictions, resamples=resamples, seed=seed, min_support=min_support
    )
    beats_baseline = diff_ci_low is not None and diff_ci_low > 0

    per_critical = critical_category_f1(predictions)
    critical_passed = all(f1 >= CRITICAL_CATEGORY_FLOOR for f1 in per_critical.values())
    micro = micro_metrics(predictions)

    return ModelAcceptanceEvidence(
        macro_f1_model=macro_model,
        macro_f1_baseline=macro_baseline,
        micro_f1_model=micro.f1,
        micro_precision_model=micro.precision,
        micro_recall_model=micro.recall,
        baseline_diff_ci95_low=diff_ci_low,
        beats_baseline=beats_baseline,
        critical_category_f1=per_critical,
        critical_categories_passed=critical_passed,
        eligible_for_deploy=beats_baseline and critical_passed,
        bootstrap_seed=seed,
        bootstrap_resamples=resamples,
    )
