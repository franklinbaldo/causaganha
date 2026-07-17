"""Mechanical validation for segmenter dataset records (RFC 0012 §11)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from segmenter_dataset.schemas import MIN_INDEPENDENT_ANNOTATIONS


if TYPE_CHECKING:
    from segmenter_dataset.schemas import AnnotationRecord, Label, ReviewRecord


_INICIO_SUFFIX = "_inicio"
_FIM_SUFFIX = "_fim"


def check_final_invariants(text: str, labels: list[Label]) -> list[str]:
    """Check bounds and forbidden overlap."""
    problems: list[str] = []
    ordered = sorted(labels, key=lambda label: (label.start, label.end))
    previous_end = -1
    for label in ordered:
        if label.end > len(text):
            problems.append(f"[{label.category}] end={label.end} exceeds text length {len(text)}")
            continue
        if label.start < previous_end:
            problems.append(
                f"[{label.category}] overlaps previous span "
                f"(start={label.start} < prev_end={previous_end})"
            )
        previous_end = max(previous_end, label.end)
    return problems


def _pair_bases(labels: list[Label]) -> set[str]:
    bases: set[str] = set()
    for label in labels:
        if label.category.endswith(_INICIO_SUFFIX):
            bases.add(label.category[: -len(_INICIO_SUFFIX)])
        elif label.category.endswith(_FIM_SUFFIX):
            bases.add(label.category[: -len(_FIM_SUFFIX)])
    return bases


def validate_pairs(
    labels: list[Label],
    *,
    allowed_unmatched: dict[str, str] | None = None,
    declared_unmatched: bool | None = None,
) -> list[str]:
    """Check pair balance and require an explicit reason for every unmatched base.

    ``declared_unmatched`` remains for backwards-compatible callers; persisted
    records use ``allowed_unmatched`` so one blanket boolean cannot authorize an
    unrelated dangling pair.
    """
    problems: list[str] = []
    unmatched_bases: set[str] = set()

    for base in sorted(_pair_bases(labels)):
        starts = sorted(
            label.start for label in labels if label.category == f"{base}{_INICIO_SUFFIX}"
        )
        ends = sorted(label.start for label in labels if label.category == f"{base}{_FIM_SUFFIX}")
        if len(ends) > len(starts):
            problems.append(
                f"{base}: {len(ends)} _fim label(s) but only {len(starts)} _inicio label(s) — "
                "orphaned or excess _fim"
            )
        elif len(starts) - len(ends) > 1:
            problems.append(
                f"{base}: {len(starts)} _inicio label(s) vs {len(ends)} _fim label(s) — "
                "unbalanced beyond the single-dangling-_inicio case"
            )
        elif len(starts) - len(ends) == 1:
            unmatched_bases.add(base)

        for start, end in zip(starts, ends, strict=False):
            if end <= start:
                problems.append(
                    f"{base}: _fim at offset {end} is not after its _inicio "
                    f"at offset {start} — inverted pair"
                )
                break

    allowed_bases = unmatched_bases if allowed_unmatched is None and declared_unmatched else set()
    if allowed_unmatched is not None:
        allowed_bases = set(allowed_unmatched)

    missing_reasons = unmatched_bases - allowed_bases
    extra_reasons = allowed_bases - unmatched_bases
    if missing_reasons:
        problems.append(
            f"record has unmatched pair(s) {sorted(missing_reasons)} but no declared "
            "allowed-unmatched reason"
        )
    if extra_reasons:
        problems.append(
            f"allowed_unmatched declares bases with no unmatched pair: {sorted(extra_reasons)}"
        )
    return problems


def validate_ontology_membership(labels: list[Label], ontology_categories: set[str]) -> list[str]:
    """Return labels whose category is outside the release ontology."""
    return [
        f"category {label.category!r} not in ontology"
        for label in labels
        if label.category not in ontology_categories
    ]


def validate_single_anchor_duplicates(
    labels: list[Label], *, allow_multiple: frozenset[str] = frozenset()
) -> list[str]:
    """Reject repeated single-anchor categories unless explicitly allowed."""
    counts: dict[str, int] = {}
    for label in labels:
        if label.category.endswith(_INICIO_SUFFIX) or label.category.endswith(_FIM_SUFFIX):
            continue
        counts[label.category] = counts.get(label.category, 0) + 1
    return [
        f"category {category!r} appears {count} times — single-anchor categories must "
        "appear at most once unless explicitly permitted"
        for category, count in sorted(counts.items())
        if count > 1 and category not in allow_multiple
    ]


def validate_record(
    text: str,
    labels: list[Label],
    ontology_categories: set[str],
    *,
    allowed_unmatched: dict[str, str] | None = None,
    declared_unmatched: bool | None = None,
    allow_multiple_single_anchor: frozenset[str] = frozenset(),
) -> list[str]:
    """Run all mechanical checks for one text-and-label record."""
    problems = check_final_invariants(text, labels)
    problems.extend(validate_ontology_membership(labels, ontology_categories))
    problems.extend(
        validate_pairs(
            labels,
            allowed_unmatched=allowed_unmatched,
            declared_unmatched=declared_unmatched,
        )
    )
    problems.extend(
        validate_single_anchor_duplicates(labels, allow_multiple=allow_multiple_single_anchor)
    )
    return problems


def annotations_are_independent(a: AnnotationRecord, b: AnnotationRecord) -> list[str]:
    """Validate RFC 0012's pairwise independence contract."""
    problems: list[str] = []
    if a.annotation_id == b.annotation_id:
        problems.append("the two annotation IDs are identical")
    if a.document_id != b.document_id:
        problems.append("annotations refer to different documents")
    if not a.is_independent_capable() or not b.is_independent_capable():
        problems.append("both annotations must be unseeded independent_full_read runs")
    if (
        a.annotator_config.model_family == b.annotator_config.model_family
        and a.annotator_id == b.annotator_id
    ):
        problems.append(
            "same model family and same annotator/run ID do not establish independent execution"
        )
    return problems


def validate_review_lineage(
    review: ReviewRecord,
    annotations_by_id: dict[str, AnnotationRecord],
    *,
    ontology_version: str,
    ontology_categories: set[str],
) -> list[str]:
    """Validate an accepted review and the exact annotations it adjudicates."""
    problems: list[str] = []
    inputs = [annotations_by_id.get(annotation_id) for annotation_id in review.input_annotation_ids]
    missing = [
        annotation_id
        for annotation_id, annotation in zip(review.input_annotation_ids, inputs, strict=True)
        if annotation is None
    ]
    if missing:
        return [f"review references missing annotation IDs: {sorted(missing)}"]

    annotations = [annotation for annotation in inputs if annotation is not None]
    if len(annotations) != MIN_INDEPENDENT_ANNOTATIONS:
        problems.append(
            "evaluation reviews must resolve exactly two annotations because the RFC IAA "
            "metric is pairwise"
        )
        return problems

    for annotation in annotations:
        if annotation.document_id != review.document_id:
            problems.append(
                f"annotation {annotation.annotation_id} belongs to {annotation.document_id}, "
                f"not review document {review.document_id}"
            )
        if annotation.ontology_version != ontology_version:
            problems.append(
                f"annotation {annotation.annotation_id} uses ontology "
                f"{annotation.ontology_version}, expected {ontology_version}"
            )
        missing_coverage = ontology_categories - set(annotation.covered_categories)
        if missing_coverage:
            problems.append(
                f"annotation {annotation.annotation_id} does not cover evaluation categories "
                f"{sorted(missing_coverage)}"
            )

    problems.extend(annotations_are_independent(annotations[0], annotations[1]))
    return problems
