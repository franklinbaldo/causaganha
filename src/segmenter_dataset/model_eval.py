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


def critical_category_f1(predictions: list[DocumentModelPrediction]) -> dict[str, float]:
    """Point-estimate pooled F1 (model vs. gold) for each RFC-fixed critical category."""
    pairs = [item.model_pair for item in predictions]
    counts = pooled_counts(pairs)
    return {
        category: f1_from_counts(*counts.get(category, (0, 0, 0)))
        for category in sorted(CRITICAL_CATEGORIES)
    }


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

    return ModelAcceptanceEvidence(
        macro_f1_model=macro_model,
        macro_f1_baseline=macro_baseline,
        baseline_diff_ci95_low=diff_ci_low,
        beats_baseline=beats_baseline,
        critical_category_f1=per_critical,
        critical_categories_passed=critical_passed,
        eligible_for_deploy=beats_baseline and critical_passed,
        bootstrap_seed=seed,
        bootstrap_resamples=resamples,
    )
