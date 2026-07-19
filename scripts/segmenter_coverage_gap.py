"""Coverage-gap analysis (RFC 0012 §5.1)."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from segmenter_dataset.store import SegmenterDatasetStore


def compute_gaps(store_dir: Path) -> dict[str, list[str]]:
    store = SegmenterDatasetStore(store_dir)
    bucket_categories = defaultdict(set)
    bucket_category_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for annotation in store.list_annotations():
        doc = store.read_document(annotation.document_id)
        bucket = f"{doc.source.system}|{annotation.annotation_method}|{annotation.annotator_id}"

        for cat in annotation.covered_categories:
            bucket_categories[bucket].add(cat)

        for label in annotation.labels:
            bucket_category_counts[bucket][label.category] += 1

    gaps: dict[str, list[str]] = {}
    for bucket, covered in bucket_categories.items():
        gaps[bucket] = []
        for cat in covered:
            if bucket_category_counts[bucket].get(cat, 0) == 0:
                gaps[bucket].append(cat)
        gaps[bucket].sort()

    return gaps


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("data/segmenter"))
    args = parser.parse_args()

    gaps = compute_gaps(args.store)

    print("Coverage Gaps by Bucket:")
    for bucket, missing in sorted(gaps.items()):
        print(f"\nBucket: {bucket}")
        if missing:
            for cat in missing:
                print(f"  - {cat}")
        else:
            print("  No gaps.")


if __name__ == "__main__":
    main()
