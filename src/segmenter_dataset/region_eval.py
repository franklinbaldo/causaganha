"""Region-level evaluation: does an anchor error damage the reconstructed
structural region the product actually consumes? (#1052)

The model predicts short ``_inicio``/``_fim`` anchor spans, while the
product consumes the structural region reconstructed by pairing them (see
``store.py``'s ``_pair_base_and_role``/``_region_interval``, whose
grouping and unmatched-anchor fallback this mirrors). Exact-span F1
(:mod:`segmenter_dataset.iaa`) tells whether the model found the expected
cue and category; it says nothing about whether that anchor error actually
damages the region delivered downstream — a boundary off by a few
characters is a very different failure from missing the region entirely.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from segmenter_dataset.schemas import Label


_PAIR_ROLES = ("inicio", "fim")


def _pair_base_and_role(category: str) -> tuple[str, str] | None:
    """``("relatorio", "inicio")`` for ``"relatorio_inicio"``; ``None`` for a single anchor."""
    for role in _PAIR_ROLES:
        suffix = f"_{role}"
        if category.endswith(suffix):
            return category[: -len(suffix)], role
    return None


def regions_from_labels(labels: tuple[Label, ...]) -> dict[str, tuple[int, int]]:
    """Reconstruct each pair category's region interval from its anchors.

    A matched pair spans ``inicio.start`` to ``fim.end``; an unmatched
    ``inicio`` or ``fim`` alone stands in for the region using its own span
    (the same fallback ``store.py`` uses when rendering an unmatched pair).
    Single-anchor categories (no ``_inicio``/``_fim`` suffix) have no
    region and are excluded.
    """
    by_base: dict[str, dict[str, Label]] = {}
    for label in labels:
        parsed = _pair_base_and_role(label.category)
        if parsed is None:
            continue
        base, role = parsed
        by_base.setdefault(base, {})[role] = label

    regions: dict[str, tuple[int, int]] = {}
    for base, roles in by_base.items():
        if "inicio" in roles and "fim" in roles:
            regions[base] = (roles["inicio"].start, roles["fim"].end)
        elif "inicio" in roles:
            regions[base] = (roles["inicio"].start, roles["inicio"].end)
        else:
            regions[base] = (roles["fim"].start, roles["fim"].end)
    return regions


def _iou(gold: tuple[int, int], predicted: tuple[int, int]) -> float:
    intersection = max(0, min(gold[1], predicted[1]) - max(gold[0], predicted[0]))
    union = (gold[1] - gold[0]) + (predicted[1] - predicted[0]) - intersection
    return intersection / union if union > 0 else 0.0


@dataclass(frozen=True)
class RegionComparison:
    """One region type's gold-vs-predicted outcome for one document."""

    base: str
    gold: tuple[int, int] | None
    predicted: tuple[int, int] | None
    start_error: int | None
    end_error: int | None
    iou: float

    @property
    def matched(self) -> bool:
        """True when both gold and a prediction exist for this region type.

        False covers two distinct failures a caller must be able to tell
        apart: gold has the region but no prediction reconstructed it
        (missed), or a prediction reconstructed a region gold doesn't have
        (hallucinated) — never conflated into the same "wrong" bucket.
        """
        return self.gold is not None and self.predicted is not None


def compare_regions(
    gold_labels: tuple[Label, ...], predicted_labels: tuple[Label, ...]
) -> list[RegionComparison]:
    """Compare reconstructed regions per category base, gold vs predicted.

    Every base present in either gold or predicted regions is reported, in
    sorted order, including a base found in only one side — so a missed
    region and a hallucinated one both stay visible instead of being
    dropped from the comparison.
    """
    gold_regions = regions_from_labels(gold_labels)
    predicted_regions = regions_from_labels(predicted_labels)
    bases = sorted(set(gold_regions) | set(predicted_regions))

    comparisons = []
    for base in bases:
        gold = gold_regions.get(base)
        predicted = predicted_regions.get(base)
        if gold is not None and predicted is not None:
            comparisons.append(
                RegionComparison(
                    base=base,
                    gold=gold,
                    predicted=predicted,
                    start_error=abs(gold[0] - predicted[0]),
                    end_error=abs(gold[1] - predicted[1]),
                    iou=_iou(gold, predicted),
                )
            )
        else:
            comparisons.append(
                RegionComparison(
                    base=base,
                    gold=gold,
                    predicted=predicted,
                    start_error=None,
                    end_error=None,
                    iou=0.0,
                )
            )
    return comparisons


def region_match_rate(comparisons: list[RegionComparison]) -> float | None:
    """Fraction of gold region types that were also reconstructed in predictions.

    ``None`` when gold has no regions at all — nothing to match against,
    distinct from ``0.0``, which means gold had regions and every one of
    them was missed.
    """
    gold_comparisons = [comparison for comparison in comparisons if comparison.gold is not None]
    if not gold_comparisons:
        return None
    matched = sum(1 for comparison in gold_comparisons if comparison.matched)
    return matched / len(gold_comparisons)
