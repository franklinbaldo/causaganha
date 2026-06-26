#!/usr/bin/env python3
r"""Evaluate regex heuristic segmenter against LLM-labeled ground truth.

Loads the LLM-labeled training parquet, runs the regex segmenter on the same
texts, and compares character-level labels. Reports per-class precision, recall,
and F1 scores.

Usage:
    uv run python scripts/evaluate_regex_segmenter.py \
        --labeled data/segmenter_training.parquet
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

import structlog

from scripts.prepare_privacy_filter_dataset import SPAN_CLASS_NAMES, _segment


logger = structlog.get_logger()

ALL_LABELS = [name for name in SPAN_CLASS_NAMES if name != "O"]


def _spans_to_char_labels(text_len: int, spans: dict[str, list]) -> list[str]:
    """Convert span dict to per-character label array."""
    labels = ["O"] * text_len
    for label_name, span_list in spans.items():
        for pair in span_list:
            start, end = int(pair[0]), int(pair[1])
            for i in range(start, min(end, text_len)):
                labels[i] = label_name
    return labels


def _compute_metrics(
    gold_chars: list[str],
    pred_chars: list[str],
) -> dict[str, dict[str, float]]:
    """Compute per-label precision, recall, F1 from char-level arrays."""
    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)

    for g, p in zip(gold_chars, pred_chars, strict=True):
        if g == p and g != "O":
            tp[g] += 1
        else:
            if p != "O":
                fp[p] += 1
            if g != "O":
                fn[g] += 1

    results: dict[str, dict[str, float]] = {}
    for label in ALL_LABELS:
        t = tp.get(label, 0)
        f_p = fp.get(label, 0)
        f_n = fn.get(label, 0)
        precision = t / (t + f_p) if (t + f_p) > 0 else 0.0
        recall = t / (t + f_n) if (t + f_n) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        support = t + f_n
        if support > 0 or f_p > 0:
            results[label] = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": support,
                "tp": t,
                "fp": f_p,
                "fn": f_n,
            }

    total_tp = sum(tp.values())
    total_fp = sum(fp.values())
    total_fn = sum(fn.values())
    macro_p = sum(r["precision"] for r in results.values()) / max(len(results), 1)
    macro_r = sum(r["recall"] for r in results.values()) / max(len(results), 1)
    macro_f1 = 2 * macro_p * macro_r / (macro_p + macro_r) if (macro_p + macro_r) > 0 else 0.0
    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0

    results["macro avg"] = {"precision": macro_p, "recall": macro_r, "f1": macro_f1, "support": 0}
    results["micro avg"] = {"precision": micro_p, "recall": micro_r, "f1": micro_f1, "support": 0}

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate regex segmenter vs LLM labels")
    parser.add_argument(
        "--labeled",
        default="data/benchmark/segmenter_training.parquet",
        help="LLM-labeled parquet with spans_json column",
    )
    args = parser.parse_args()

    import ibis

    t = ibis.read_parquet(args.labeled)
    df = t.execute()
    logger.info("loaded_labeled", count=len(df))

    all_gold_chars: list[str] = []
    all_pred_chars: list[str] = []
    skipped = 0

    for _, row in df.iterrows():
        texto = row["texto"]
        gold_spans = json.loads(row["spans_json"])
        pred_spans = _segment(texto)
        if pred_spans is None:
            pred_spans = {}

        gold_chars = _spans_to_char_labels(len(texto), gold_spans)
        pred_chars = _spans_to_char_labels(len(texto), pred_spans)
        all_gold_chars.extend(gold_chars)
        all_pred_chars.extend(pred_chars)

        if pred_spans is None:
            skipped += 1

    logger.info("evaluation_done", texts=len(df), skipped=skipped)

    results = _compute_metrics(all_gold_chars, all_pred_chars)

    print("\n" + "=" * 78)
    print("REGEX SEGMENTER vs LLM LABELS — Character-level Evaluation")
    print("=" * 78)
    print(f"{'Label':<25} {'Prec':>7} {'Rec':>7} {'F1':>7} {'Support':>9}")
    print("-" * 78)

    section_labels = [la for la in ALL_LABELS if la.startswith("sec_") or la == "elem_nao_textual"]
    entity_labels = [la for la in ALL_LABELS if la not in section_labels]

    print("  SECTIONS:")
    for label in section_labels:
        if label in results:
            r = results[label]
            print(
                f"  {label:<23} {r['precision']:>7.3f} {r['recall']:>7.3f} "
                f"{r['f1']:>7.3f} {r['support']:>9.0f}"
            )

    print("\n  ENTITIES:")
    for label in entity_labels:
        if label in results:
            r = results[label]
            print(
                f"  {label:<23} {r['precision']:>7.3f} {r['recall']:>7.3f} "
                f"{r['f1']:>7.3f} {r['support']:>9.0f}"
            )

    print("-" * 78)
    for avg in ("macro avg", "micro avg"):
        r = results[avg]
        print(f"  {avg:<23} {r['precision']:>7.3f} {r['recall']:>7.3f} {r['f1']:>7.3f}")
    print("=" * 78)

    return 0


if __name__ == "__main__":
    sys.exit(main())
