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

from segmenter_dataset.splits import evaluation_eligible_document_ids, train_eligible_document_ids
from segmenter_dataset.store import SegmenterDatasetStore


def compute_governance_status(store_dir: Path) -> dict[str, int | bool]:
    store = SegmenterDatasetStore(store_dir)
    documents = list(store.list_documents())
    annotations = list(store.list_annotations())
    reviews = list(store.list_reviews())

    train_eligible = train_eligible_document_ids(annotations)
    evaluation_eligible = evaluation_eligible_document_ids(reviews)

    return {
        "document_count": len(documents),
        "annotation_count": len(annotations),
        "review_count": len(reviews),
        "train_eligible_count": len(train_eligible),
        "evaluation_eligible_count": len(evaluation_eligible),
        "blocked_on_reviews": len(documents) > 0 and len(evaluation_eligible) == 0,
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


if __name__ == "__main__":
    main()
