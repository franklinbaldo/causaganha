"""Shared opf command construction and metric reporting.

Single source of truth for how CausaGanha invokes ``opf train`` / ``opf eval``
and how the canonical macro F1 is computed from opf's metrics JSON. Used by
both the local runner (``train_decision_segmenter.py``) and the Colab driver
(``colab_train_driver.py``) so a CLI change or metric correction is made once.

STDLIB-ONLY on purpose: the Colab driver uploads this file to a bare runtime
where no repo dependency (structlog, torch, ibis) is installed.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from pathlib import Path


def build_opf_train_cmd(
    train_jsonl: Path,
    val_jsonl: Path,
    label_space_json: Path,
    output_dir: Path,
    *,
    device: str,
    epochs: int,
    batch_size: int,
    python: str = sys.executable,
) -> list[str]:
    return [
        python,
        "-m",
        "opf",
        "train",
        str(train_jsonl),
        "--validation-dataset",
        str(val_jsonl),
        "--label-space-json",
        str(label_space_json),
        "--output-dir",
        str(output_dir),
        "--device",
        device,
        "--epochs",
        str(epochs),
        "--batch-size",
        str(batch_size),
    ]


def build_opf_eval_cmd(
    test_jsonl: Path,
    checkpoint_dir: Path,
    metrics_out: Path,
    *,
    device: str,
    python: str = sys.executable,
) -> list[str]:
    return [
        python,
        "-m",
        "opf",
        "eval",
        str(test_jsonl),
        "--checkpoint",
        str(checkpoint_dir),
        "--device",
        device,
        "--per-class",
        "--metrics-out",
        str(metrics_out),
    ]


def compute_macro_f1(metrics: dict, span_class_names: list[str]) -> dict:
    """Canonical macro F1: mean of per-class F1s, NOT detection.span.f1.

    OPF uses flat keys like ``detection.span.f1`` and
    ``by_class.<label>.span.f1``. The aggregate detection F1 is misleading
    under class imbalance, so the project metric is the mean of per-class F1s
    (also reported excluding ``ref_normativa``, which dominates support).

    Returns ``{"per_class": {cat: f1}, "macro_f1": float,
    "macro_f1_no_ref": float, "detection_f1": float | None}``.
    """
    per_class: dict[str, float] = {}
    detection_f1 = metrics.get("detection.span.f1")
    for cat in span_class_names:
        if cat == "O":
            continue
        f1 = metrics.get(f"by_class.{cat}.span.f1")
        if f1 is None:
            cat_metrics = metrics.get(cat)
            f1 = cat_metrics.get("f1-score") if isinstance(cat_metrics, dict) else None
        if f1 is not None:
            per_class[cat] = f1

    f1s = list(per_class.values())
    f1s_no_ref = [f1 for cat, f1 in per_class.items() if cat != "ref_normativa"]
    macro = sum(f1s) / len(f1s) if f1s else (detection_f1 or 0.0)
    macro_no_ref = sum(f1s_no_ref) / len(f1s_no_ref) if f1s_no_ref else macro
    return {
        "per_class": per_class,
        "macro_f1": macro,
        "macro_f1_no_ref": macro_no_ref,
        "detection_f1": detection_f1,
    }
