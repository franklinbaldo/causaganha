#!/usr/bin/env python3
r"""Train CausaGanha decision segmenter via opf CLI (openai/privacy-filter).

Consumes a FROZEN artifact set (train.jsonl, val.jsonl, test.jsonl,
label_space.json) produced by the prep script. Never re-derives inputs.

Usage:
    # From pre-prepared artifacts (recommended):
    uv run python scripts/train_decision_segmenter.py \
        --data-dir data/segmenter_v7 \
        --output-dir models/decision_segmenter

    # Prepare-only (write JSONL from parquet, skip training):
    uv run python scripts/train_decision_segmenter.py \
        --prepare-from data/test_parquets/textos.parquet \
        --output-dir data/segmenter_v7
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import structlog


logger = structlog.get_logger()


def _detect_device() -> str:
    try:
        import torch  # noqa: PLC0415

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def _load_label_space(path: Path) -> dict:
    ls = json.loads(path.read_text(encoding="utf-8"))
    names = ls.get("span_class_names", [])
    if not names or names[0] != "O":
        msg = f"Invalid label space: O must be first in span_class_names (got {names[:3]})"
        raise ValueError(msg)
    return ls


def run_opf_train(
    train_jsonl: Path,
    val_jsonl: Path,
    label_space_json: Path,
    output_dir: Path,
    *,
    epochs: int = 3,
    batch_size: int = 8,
) -> int:
    device = _detect_device()
    cmd = [
        sys.executable,
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
    logger.info("opf_train_start", cmd=" ".join(cmd), device=device)
    result = subprocess.run(cmd, check=False)
    logger.info("opf_train_done", returncode=result.returncode)
    return result.returncode


def run_opf_eval(
    test_jsonl: Path,
    model_dir: Path,
    metrics_output: Path,
) -> dict | None:
    device = _detect_device()
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "opf",
        "eval",
        str(test_jsonl),
        "--checkpoint",
        str(model_dir),
        "--device",
        device,
        "--per-class",
        "--metrics-out",
        str(metrics_output),
    ]
    logger.info("opf_eval_start", cmd=" ".join(cmd), device=device)
    result = subprocess.run(cmd, check=False)
    logger.info("opf_eval_done", returncode=result.returncode)

    if result.returncode != 0:
        return None
    if metrics_output.exists():
        try:
            return json.loads(metrics_output.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            pass
    return None


def validate_artifacts(data_dir: Path) -> bool:
    """Run opf_annotate.py validate on all splits."""
    ls_path = data_dir / "label_space.json"
    ok = True
    for split in ("train", "val", "test"):
        jsonl = data_dir / f"{split}.jsonl"
        if not jsonl.exists():
            logger.error("missing_split", split=split, path=str(jsonl))
            ok = False
            continue
        cmd = [
            sys.executable,
            str(Path(__file__).parent / "opf_annotate.py"),
            "validate",
            str(jsonl),
        ]
        if ls_path.exists():
            cmd.extend(["--label-space", str(ls_path)])
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            logger.error("validation_failed", split=split)
            ok = False
        else:
            logger.info("validation_passed", split=split)
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Train CausaGanha segmenter via opf")
    parser.add_argument(
        "--data-dir",
        help="Directory with frozen artifacts (train/val/test.jsonl + label_space.json)",
    )
    parser.add_argument(
        "--prepare-from",
        metavar="PARQUET",
        help="Run prep script to generate artifacts from parquet, then exit",
    )
    parser.add_argument(
        "--output-dir",
        default="models/decision_segmenter",
        help="Output directory for model and metrics",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Write JSONL + label_space.json but skip training/eval",
    )
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)

    # Mode 1: prepare from parquet
    if args.prepare_from:
        from scripts.prepare_privacy_filter_dataset import main as prep_main  # noqa: PLC0415

        sys.argv = [
            "prepare",
            "--bootstrap",
            "--parquet",
            args.prepare_from,
            "--output-dir",
            str(output_dir),
        ]
        return prep_main()

    # Mode 2: train from frozen artifacts
    data_dir = Path(args.data_dir) if args.data_dir else output_dir
    required = ["train.jsonl", "val.jsonl", "test.jsonl", "label_space.json"]
    missing = [f for f in required if not (data_dir / f).exists()]
    if missing:
        logger.error("missing_artifacts", data_dir=str(data_dir), missing=missing)
        print(
            f"Error: missing {missing} in {data_dir}. Run prep script first or use --prepare-from.",
            file=sys.stderr,
        )
        return 1

    ls = _load_label_space(data_dir / "label_space.json")
    num_categories = len(ls["span_class_names"])
    logger.info(
        "label_space_loaded",
        version=ls.get("category_version"),
        categories=num_categories,
    )

    if not args.skip_validation and not validate_artifacts(data_dir):
        logger.error("validation_failed_aborting")
        return 1

    if args.prepare_only:
        print(f"\nData validated in {data_dir}/")
        print(f"  categories: {num_categories} ({num_categories - 1} + O)")
        print("\nTo train, run on a machine with GPU:")
        print(f"  opf train {data_dir}/train.jsonl \\")
        print(f"    --validation-dataset {data_dir}/val.jsonl \\")
        print(f"    --label-space-json {data_dir}/label_space.json \\")
        print(f"    --output-dir {output_dir / 'best'}")
        return 0

    # Train
    checkpoint_dir = output_dir / "best"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    rc = run_opf_train(
        data_dir / "train.jsonl",
        data_dir / "val.jsonl",
        data_dir / "label_space.json",
        checkpoint_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )
    if rc != 0:
        logger.error("opf_train_failed", returncode=rc)
        return rc

    # Evaluate
    metrics_path = output_dir / "test_metrics.json"
    metrics = run_opf_eval(data_dir / "test.jsonl", checkpoint_dir, metrics_path)
    if not metrics:
        logger.error("opf_eval_failed")
        return 1

    # Report — derive category names from label_space, not hardcoded.
    # OPF uses flat keys like "detection.span.f1" and "by_class.<label>.span.f1".
    # Compute true macro F1 as mean of per-class F1 (not detection.span.f1 which
    # is the aggregate and misleading under class imbalance).
    per_class_f1s: list[float] = []
    detection_f1 = metrics.get("detection.span.f1")
    for cat in ls["span_class_names"]:
        if cat == "O":
            continue
        f1 = metrics.get(f"by_class.{cat}.span.f1")
        if f1 is not None:
            per_class_f1s.append(f1)
            print(f"  {cat}: F1={f1:.3f}")
        else:
            cat_metrics = metrics.get(cat, {})
            if cat_metrics:
                cf1 = cat_metrics.get("f1-score", 0)
                per_class_f1s.append(cf1)
                print(f"  {cat}: F1={cf1:.3f}")

    macro_f1 = sum(per_class_f1s) / len(per_class_f1s) if per_class_f1s else (detection_f1 or 0)
    print(f"\nMacro F1 (mean of {len(per_class_f1s)} classes): {macro_f1:.3f}")
    if detection_f1 is not None:
        print(f"Detection F1 (aggregate): {detection_f1:.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
