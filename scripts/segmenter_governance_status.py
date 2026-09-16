#!/usr/bin/env python3
"""Report segmenter_dataset store governance status (RFC 0012 §10, issue #1051).

``assign_splits`` requires an *accepted* :class:`~segmenter_dataset.schemas.ReviewRecord`
before a document is eligible for the validation/test role. When the store has
zero reviews, ``assign-splits`` silently produces an empty val/test manifest
instead of raising — correct per ``EmptyEvalSplitError``'s own docstring
(it only guards *starved* eligible groups, not a genuinely empty eligible
set). Nothing else surfaces that fact on its own, so this script makes the
store's review/eligibility state an explicit, checkable report.

Usage:
    uv run python scripts/segmenter_governance_status.py --store data/segmenter
"""

from __future__ import annotations

import argparse
import json
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


# RFC 0012 Sec 5 item 4: >= 30 validation documents adjudicated, >= 30 test
# documents adjudicated. This is a floor per split, not a combined total.
RFC_0012_SPLIT_FLOOR = 30

# Same defaults as `segmenter_dataset assign-splits` (src/segmenter_dataset/__main__.py).
_DEFAULT_TRAIN_RATIO = 0.70
_DEFAULT_VAL_RATIO = 0.15
_DEFAULT_SEED = 0


def _val_test_counts(
    *,
    groups: dict[str, frozenset[str]],
    train_eligible: frozenset[str],
    evaluation_eligible: frozenset[str],
) -> tuple[int, int]:
    """Real val/test counts `assign_splits` would produce for this eligibility split.

    Returns ``(0, 0)`` on :class:`EmptyEvalSplitError` -- that error means
    eligible groups exist but got starved to zero by greedy packing, which is
    itself a "0 achieved" outcome for this diagnostic's purposes.
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


def compute_governance_status(store_dir: Path) -> dict[str, int | bool]:
    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    annotations = list(store.list_annotations())
    reviews = list(store.list_reviews())

    train_eligible = train_eligible_document_ids(annotations)
    evaluation_eligible = evaluation_eligible_document_ids(reviews)

    grouping_keys = [GroupingKeys.from_document(doc) for doc in documents]
    groups = build_groups(documents, grouping_keys)

    val_count, test_count = _val_test_counts(
        groups=groups, train_eligible=train_eligible, evaluation_eligible=evaluation_eligible
    )
    # Ceiling: what val/test would be if every train-eligible document were
    # *also* adjudicated today -- isolates the corpus-size ceiling (#1050)
    # from the review-coverage gap (#1051).
    val_ceiling, test_ceiling = _val_test_counts(
        groups=groups, train_eligible=train_eligible, evaluation_eligible=train_eligible
    )

    meets_floor = val_count >= RFC_0012_SPLIT_FLOOR and test_count >= RFC_0012_SPLIT_FLOOR
    corpus_scale_blocks_floor = (
        val_ceiling < RFC_0012_SPLIT_FLOOR or test_ceiling < RFC_0012_SPLIT_FLOOR
    )

    return {
        "document_count": len(documents),
        "annotation_count": len(annotations),
        "review_count": len(reviews),
        "train_eligible_count": len(train_eligible),
        "evaluation_eligible_count": len(evaluation_eligible),
        "blocked_on_reviews": len(documents) > 0 and len(evaluation_eligible) == 0,
        "val_count": val_count,
        "test_count": test_count,
        "val_ceiling_at_full_adjudication": val_ceiling,
        "test_ceiling_at_full_adjudication": test_ceiling,
        "meets_rfc_0012_split_floor": meets_floor,
        "corpus_scale_blocks_floor": corpus_scale_blocks_floor,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("data/segmenter"))
    args = parser.parse_args(argv)

    status = compute_governance_status(args.store)
    print(json.dumps(status, indent=2))

    if status["blocked_on_reviews"]:
        print(
            "\nWARNING: 0 evaluation-eligible documents "
            f"(no accepted ReviewRecord in {args.store}/reviews/) despite "
            f"{status['document_count']} documents in the store. "
            "`assign-splits` will produce an empty val/test split until "
            "adjudicated reviews exist -- see issue #1051.",
        )
    elif status["corpus_scale_blocks_floor"]:
        print(
            "\nWARNING: RFC 0012 Sec 5 item 4's per-split floor "
            f"(>= {RFC_0012_SPLIT_FLOOR} val, >= {RFC_0012_SPLIT_FLOOR} test, each "
            f"adjudicated) cannot be reached with the current corpus size "
            f"({status['document_count']} documents), even at 100% adjudication: "
            f"val_ceiling={status['val_ceiling_at_full_adjudication']}, "
            f"test_ceiling={status['test_ceiling_at_full_adjudication']}. "
            "Adjudicating more of the existing pool (#1051) cannot cross this "
            "ceiling -- growing the total corpus is required (#1050).",
        )


if __name__ == "__main__":
    main()
