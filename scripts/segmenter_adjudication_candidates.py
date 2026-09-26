#!/usr/bin/env python3
"""Formalize the #1051 "simulate before annotate" candidate-selection method.

RFC 0012 Sec 5 item 4's val/test floor (>= 30 each, adjudicated) only moves
when a document with exactly one unseeded annotation gets a second,
genuinely independent annotation and is adjudicated into an accepted
``ReviewRecord`` (``segmenter_dataset.splits.evaluation_eligible_document_ids``).
Every #1051 round so far (ns7mbo/ku8qje/p08457/kgxf50/bomtmk/uq3be8/
pg2bcv/6m3b2b -- see ``knowledge/backlog/issue-1051.md``) re-derived the same
candidate scan and ``assign_splits`` simulation from scratch, in a throwaway
script written fresh each time. This module commits that method as tested,
reusable code instead: a candidate is only worth spending annotation effort
on if adding it to ``evaluation_eligible`` *actually* raises ``test_count``
(``assign_splits`` recomputes the whole val/test partition from a fixed hash
order of ``(seed, group_id)`` on every call, so which specific document lands
in val vs. test is not identity-controllable -- only the aggregate counts are
a real, checkable contract, per every #1051 round's own
``decision-simulate-before-annotating`` notes).

This script does not itself produce a second annotation or a review -- see
``scripts/annotate_second_independent.py`` and
``scripts/adjudicate_segmenter_review.py`` for that. It only answers "which
of the remaining single-annotated documents are worth the effort, and in
what combination."

Usage::

    uv run python scripts/segmenter_adjudication_candidates.py --top 15
    uv run python scripts/segmenter_adjudication_candidates.py \\
        --simulate doc_aaa... doc_bbb...
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from segmenter_dataset.splits import (
    EmptyEvalSplitError,
    GroupingKeys,
    assign_splits,
    build_groups,
    evaluation_eligible_document_ids,
    train_eligible_document_ids,
)
from segmenter_dataset.store import SegmenterDatasetStore


# Same defaults as `segmenter_dataset assign-splits` / segmenter_governance_status.py.
_DEFAULT_TRAIN_RATIO = 0.70
_DEFAULT_VAL_RATIO = 0.15
_DEFAULT_SEED = 0


@dataclass(frozen=True)
class CandidateInfo:
    """One single-annotated, unreviewed, eligible-to-be-adjudicated document."""

    document_id: str
    tribunal: str
    document_type: str
    source_uri: str
    text_length: int
    individually_raises_test_count: bool


def _val_test_counts(
    *,
    groups: dict[str, frozenset[str]],
    train_eligible: frozenset[str],
    evaluation_eligible: frozenset[str],
) -> tuple[int, int]:
    """Real val/test counts `assign_splits` would produce for this eligibility split.

    Returns ``(0, 0)`` on :class:`EmptyEvalSplitError` -- an eligible-but-starved
    outcome is itself a "0 achieved" result for this diagnostic's purposes
    (same convention as ``scripts/segmenter_governance_status.py``).
    """
    try:
        assignment = assign_splits(
            groups,
            train_eligible=train_eligible,
            evaluation_eligible=evaluation_eligible,
            train_ratio=_DEFAULT_TRAIN_RATIO,
            val_ratio=_DEFAULT_VAL_RATIO,
            seed=_DEFAULT_SEED,
        )
    except EmptyEvalSplitError:
        return 0, 0
    return len(assignment.val_ids), len(assignment.test_ids)


def find_second_annotation_candidates(store_dir: Path) -> list[CandidateInfo]:
    """Single-annotated, ``seeded_with=='none'``, unreviewed documents, shortest-first.

    A document whose sole annotation has ``seeded_with != 'none'`` can never
    form an independent pair (``mechanical.annotations_are_independent``
    requires both inputs unseeded) -- filtered out here so a caller never
    wastes annotation effort choosing it. A document with an existing review
    (accepted or not) is also excluded: it already went through adjudication
    once, and this scan is only for documents still waiting on their first
    review attempt.

    Sorted shortest-document-first, the same tractability heuristic every
    #1051 round has used to bound per-document reading/annotation effort.
    """
    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    annotations = list(store.list_annotations())
    reviews = list(store.list_reviews())

    docs_by_id = {doc.document_id: doc for doc in documents}
    annotations_by_doc: dict[str, list] = {}
    for annotation in annotations:
        annotations_by_doc.setdefault(annotation.document_id, []).append(annotation)
    reviewed_document_ids = {review.document_id for review in reviews}

    train_eligible = train_eligible_document_ids(annotations)
    evaluation_eligible = evaluation_eligible_document_ids(reviews)
    grouping_keys = [GroupingKeys.from_document(doc) for doc in documents]
    groups = build_groups(documents, grouping_keys)
    _, base_test_count = _val_test_counts(
        groups=groups, train_eligible=train_eligible, evaluation_eligible=evaluation_eligible
    )

    candidates: list[CandidateInfo] = []
    for document_id, doc_annotations in annotations_by_doc.items():
        if len(doc_annotations) != 1 or document_id in reviewed_document_ids:
            continue
        if doc_annotations[0].annotator_config.seeded_with != "none":
            continue

        trial_eligible = evaluation_eligible | {document_id}
        _, trial_test_count = _val_test_counts(
            groups=groups, train_eligible=train_eligible, evaluation_eligible=trial_eligible
        )
        document = docs_by_id[document_id]
        candidates.append(
            CandidateInfo(
                document_id=document_id,
                tribunal=document.source.tribunal,
                document_type=document.source.document_type,
                source_uri=document.source.source_uri,
                text_length=len(document.text),
                individually_raises_test_count=trial_test_count > base_test_count,
            )
        )

    return sorted(candidates, key=lambda candidate: candidate.text_length)


def joint_simulation(store_dir: Path, document_ids: list[str]) -> tuple[int, int]:
    """``(val_count, test_count)`` if every id in ``document_ids`` were also adjudicated.

    Confirms the *aggregate* effect of a whole round's batch before any
    annotation effort is spent -- an individually-raising candidate can still
    net to zero once combined with others, since `assign_splits` repacks the
    whole partition every call.
    """
    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    annotations = list(store.list_annotations())
    reviews = list(store.list_reviews())
    train_eligible = train_eligible_document_ids(annotations)
    evaluation_eligible = evaluation_eligible_document_ids(reviews) | set(document_ids)
    grouping_keys = [GroupingKeys.from_document(doc) for doc in documents]
    groups = build_groups(documents, grouping_keys)
    return _val_test_counts(
        groups=groups, train_eligible=train_eligible, evaluation_eligible=evaluation_eligible
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("data/segmenter"))
    parser.add_argument(
        "--top", type=int, default=15, help="how many shortest raising candidates to print"
    )
    parser.add_argument(
        "--simulate",
        nargs="+",
        default=None,
        metavar="DOCUMENT_ID",
        help="jointly simulate adding these document_ids to evaluation_eligible",
    )
    args = parser.parse_args(argv)

    candidates = find_second_annotation_candidates(args.store)
    raising = [c for c in candidates if c.individually_raises_test_count]

    print(
        json.dumps(
            {
                "total_candidates": len(candidates),
                "individually_raising_test_count": len(raising),
            },
            indent=2,
        )
    )
    print(f"\nShortest {min(args.top, len(raising))} raising candidates:")
    for candidate in raising[: args.top]:
        print(json.dumps(asdict(candidate)))

    if args.simulate:
        val_count, test_count = joint_simulation(args.store, args.simulate)
        print(
            "\n"
            + json.dumps(
                {
                    "joint_simulation": {
                        "document_ids": args.simulate,
                        "val_count": val_count,
                        "test_count": test_count,
                    }
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
