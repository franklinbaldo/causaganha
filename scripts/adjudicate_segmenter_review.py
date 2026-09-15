r"""Adjudicate a pair of independent annotations into a ReviewRecord.

RFC 0012 §8 ("Registro de review (adjudicação)") and §9 ("Dados de
validação e teste"): a val/test document becomes evaluation-eligible
(``segmenter_dataset.splits.evaluation_eligible_document_ids``) only once an
*accepted* review exists for it, resolving two independent annotations.

This script does not compute the resolution automatically — the reviewer
(a human, or in the ``silver`` tier RFC 0012 §9.1 already permits, an LLM/
agent acting as the "Revisor" role) supplies their own fully tagged
reproduction of the document (``--resolution-file``, same shape as an
annotation, §8) after examining both inputs' disagreements. ``diff_labels``
exists so that examination has a precise, code-checked account of what the
two annotations actually disagreed on, rather than an eyeballed guess.

Independence (RFC 0012 §5.3) is deliberately *not* re-checked here — it
already lives at persistence time in
``SegmenterDatasetStore.write_review``'s ``NonIndependentReviewError`` guard.
This module's job is only to build a well-formed ``ReviewRecord`` candidate
and let that existing guard be the actual enforcement point.

Usage::

    uv run python scripts/adjudicate_segmenter_review.py \
        --data-root data/segmenter \
        --document-id doc_57d1c65ce480854290dc81fd59d4827d \
        --annotation-a ann_... --annotation-b ann_... \
        --resolution-file /path/to/adjudicated_tagged.txt \
        --reviewers segmenter_dataset_agent_review:v1 \
        --resolution "adopted annotation B's fundamentacao_legal/custas spans; see notes" \
        --approved-at 2026-09-15T09:00:00Z
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from segmenter_dataset.ids import review_id as build_review_id
from segmenter_dataset.mechanical import validate_record
from segmenter_dataset.ontology import ALLOW_MULTIPLE_SINGLE_ANCHOR, load_categories
from segmenter_dataset.schemas import AnnotationRecord, DocumentRecord, Label, ReviewRecord
from segmenter_dataset.store import SegmenterDatasetStore, _text_element_to_labels


class VerbatimFidelityError(ValueError):
    """The resolution's tagged reproduction, tags stripped, doesn't match the document."""


class MechanicalValidationError(ValueError):
    """The resolution's final labels fail RFC 0012 §11 mechanical validation."""


@dataclass(frozen=True)
class LabelDiff:
    """Exact-match partition of two annotations' labels — the adjudicator's map of work.

    ``matched`` is what the two annotators already agree on and needs no
    adjudication; ``only_a``/``only_b`` are exactly the spans a reviewer must
    look at and decide whether to keep, in the resolution.
    """

    matched: tuple[Label, ...]
    only_a: tuple[Label, ...]
    only_b: tuple[Label, ...]


def _sort_key(label: Label) -> tuple[int, int, str]:
    return (label.start, label.end, label.category)


def diff_labels(labels_a: list[Label], labels_b: list[Label]) -> LabelDiff:
    """Exact-match (``start``, ``end``, ``category``) diff — RFC 0012 §8's own matching rule."""
    keyed_a = {(label.start, label.end, label.category): label for label in labels_a}
    keyed_b = {(label.start, label.end, label.category): label for label in labels_b}
    matched_keys = keyed_a.keys() & keyed_b.keys()
    only_a_keys = keyed_a.keys() - keyed_b.keys()
    only_b_keys = keyed_b.keys() - keyed_a.keys()
    return LabelDiff(
        matched=tuple(sorted((keyed_a[key] for key in matched_keys), key=_sort_key)),
        only_a=tuple(sorted((keyed_a[key] for key in only_a_keys), key=_sort_key)),
        only_b=tuple(sorted((keyed_b[key] for key in only_b_keys), key=_sort_key)),
    )


def summarize_diff(diff: LabelDiff) -> str:
    """Human-readable disagreement summary, recorded in the review's ``notes`` (§8)."""
    return (
        f"exact-match diff before adjudication: {len(diff.matched)} span(s) agreed by both "
        f"annotators, {len(diff.only_a)} only in annotation A, {len(diff.only_b)} only in "
        f"annotation B — categories in A-only: "
        f"{sorted({label.category for label in diff.only_a})}; "
        f"categories in B-only: {sorted({label.category for label in diff.only_b})}"
    )


def _parse_tagged(tagged_text: str) -> tuple[str, list[Label]]:
    root = ET.fromstring(f"<text>{tagged_text.strip()}</text>")  # noqa: S314 -- own trusted reviewer output, verified below
    return _text_element_to_labels(root)


def build_review(
    document: DocumentRecord,
    annotation_a: AnnotationRecord,
    annotation_b: AnnotationRecord,
    resolution_tagged_text: str,
    *,
    reviewers: tuple[str, ...],
    resolution: str,
    approved_at: str,
    ontology_categories: set[str],
    notes: tuple[str, ...] = (),
    allowed_unmatched: dict[str, str] | None = None,
) -> ReviewRecord:
    """Build an ``accepted`` :class:`ReviewRecord` from two annotations plus a resolution.

    ``resolution_tagged_text`` is the reviewer's own complete tagged
    reproduction of ``document.text`` — verified for verbatim fidelity and
    mechanical validity exactly like an annotation (§8, §11) before being
    trusted as ``final_labels``. The exact-match diff between ``annotation_a``
    and ``annotation_b`` is always recorded as a note, regardless of how the
    reviewer resolved it, so a later reader can see what disagreed without
    re-deriving it.
    """
    reconstructed_text, final_labels = _parse_tagged(resolution_tagged_text)
    if reconstructed_text != document.text:
        message = (
            f"verbatim-fidelity mismatch for {document.document_id!r}: the resolution's "
            f"reconstructed text differs from the stored document (len {len(reconstructed_text)} "
            f"vs {len(document.text)})"
        )
        raise VerbatimFidelityError(message)

    allowed_unmatched = allowed_unmatched or {}
    problems = validate_record(
        document.text,
        final_labels,
        ontology_categories,
        allowed_unmatched=allowed_unmatched,
        allow_multiple_single_anchor=ALLOW_MULTIPLE_SINGLE_ANCHOR,
    )
    if problems:
        message = f"mechanical validation failed for {document.document_id!r}: {problems}"
        raise MechanicalValidationError(message)

    diff = diff_labels(list(annotation_a.labels), list(annotation_b.labels))
    all_notes = (*notes, summarize_diff(diff))

    return ReviewRecord(
        review_id=build_review_id(
            document_id=document.document_id,
            input_annotation_ids=[annotation_a.annotation_id, annotation_b.annotation_id],
            approved_at=approved_at,
        ),
        document_id=document.document_id,
        input_annotation_ids=(annotation_a.annotation_id, annotation_b.annotation_id),
        status="accepted",
        final_labels=final_labels,
        allowed_unmatched=allowed_unmatched,
        reviewers=reviewers,
        resolution=resolution,
        notes=all_notes,
        approved_at=approved_at,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/segmenter"))
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--annotation-a", required=True, help="annotation_id")
    parser.add_argument("--annotation-b", required=True, help="annotation_id")
    parser.add_argument("--resolution-file", type=Path, required=True)
    parser.add_argument("--reviewers", nargs="+", required=True)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--approved-at", required=True)
    parser.add_argument("--note", action="append", default=[])
    parser.add_argument(
        "--label-space", type=Path, default=Path("data/segmenter_splits/label_space.json")
    )
    parser.add_argument("--allowed-unmatched", default="{}", help="JSON object, base -> reason")
    args = parser.parse_args(argv)

    store = SegmenterDatasetStore(args.data_root)
    document = store.read_document(args.document_id)
    annotations = {a.annotation_id: a for a in store.list_annotations(args.document_id)}
    annotation_a = annotations[args.annotation_a]
    annotation_b = annotations[args.annotation_b]
    resolution_text = args.resolution_file.read_text(encoding="utf-8")
    ontology_categories = load_categories(args.label_space)

    review = build_review(
        document,
        annotation_a,
        annotation_b,
        resolution_text,
        reviewers=tuple(args.reviewers),
        resolution=args.resolution,
        approved_at=args.approved_at,
        ontology_categories=ontology_categories,
        notes=tuple(args.note),
        allowed_unmatched=json.loads(args.allowed_unmatched),
    )
    store.write_review(review)
    print(f"Wrote review {review.review_id} for {document.document_id}")


if __name__ == "__main__":
    main()
