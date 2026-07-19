"""Compute per-category train support (RFC 0012 §5.4)."""

from __future__ import annotations

import argparse
from pathlib import Path

from segmenter_dataset.ontology import CRITICAL_CATEGORIES, load_categories
from segmenter_dataset.store import SegmenterDatasetStore


def compute_support(store_dir: Path, label_space_path: Path) -> dict[str, int]:
    store = SegmenterDatasetStore(store_dir)
    trainable_categories = load_categories(label_space_path)
    counts: dict[str, int] = dict.fromkeys(trainable_categories, 0)

    for annotation in store.list_annotations():
        for label in annotation.labels:
            if label.category.endswith("_fim"):
                continue
            if label.category in counts:
                counts[label.category] += 1
            if label.category.endswith("_inicio"):
                fim_cat = label.category[: -len("_inicio")] + "_fim"
                if fim_cat in counts:
                    counts[fim_cat] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("data/segmenter"))
    parser.add_argument(
        "--label-space",
        type=Path,
        default=Path("data/segmenter_splits/label_space.json"),
    )
    args = parser.parse_args()

    counts = compute_support(args.store, args.label_space)

    print(f"Per-category support (out of {len(counts)} categories):")
    below_floor = []
    missing_critical = []

    for cat, count in sorted(counts.items()):
        print(f"  {cat}: {count}")
        if count < 10:
            below_floor.append((cat, count))
            if cat in CRITICAL_CATEGORIES:
                missing_critical.append(cat)

    if below_floor:
        print("\nCategories below §5.4 floor of 10:")
        for cat, count in below_floor:
            print(f"  {cat}: {count}")
    else:
        print("\nAll categories meet the §5.4 floor of 10.")

    if missing_critical:
        print("\nCRITICAL CATEGORIES BELOW FLOOR:")
        for cat in missing_critical:
            print(f"  {cat}")


if __name__ == "__main__":
    main()
