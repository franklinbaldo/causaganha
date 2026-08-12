#!/usr/bin/env python3
r"""Train the CausaGanha segmenter baseline against train+val ONLY (RFC 0012 §13/§15 PR3).

Deliberately narrower than the pre-RFC `scripts/train_decision_segmenter.py`:
this script never opens `test.jsonl`, even if it happens to exist alongside
`train.jsonl`/`val.jsonl` in `--data-dir`. RFC 0012 §3.3 ("o teste e
avaliado uma unica vez") is a process rule about what the *test data* is
used for, not about who is running the script -- a trainer that reads test
every epoch violates it regardless of intent, which is exactly what the
pre-RFC script did (it called `opf eval` on test.jsonl in the same run as
training). Test evaluation is a separate, explicitly gated step: see
`scripts/run_segmenter_test_eval.py`.

Expects `--data-dir` to already contain `train.jsonl`, `val.jsonl`, and
`label_space.json` -- the output of
`segmenter_dataset.opf_export.export_release_for_training`. This script
does not derive those from a release itself; it consumes a frozen export.

Loops epoch-by-epoch with an explicit checkpoint hand-off between `opf
train` subprocess calls, rather than one `--epochs N` call -- a mechanical
lesson RFC 0012 §13.2 carries over from PR #832: the opf trainer leaks RAM
in a long-lived process. Checkpoint selection is macro-F1 on validation
only (RFC 0012 §5 point 5): highest wins; ties broken by lowest epoch, then
by lowest validation loss.

Usage:
    uv run python scripts/run_segmenter_training.py \
        --data-dir dataset-releases/segmenter-real-v8.1/opf-export \
        --output-dir training-runs/segmenter-real-v8.1 \
        --release-id segmenter-real-v8.1 \
        --ontology-version segmenter-ontology-v8.0.0 \
        --guideline-version v7.3 \
        --dependency-lock-hash <sha256 of uv.lock>

Verified against a real `opf train` on a GPU Kaggle kernel (2026-07-19,
synthetic release, not real corpus data -- the real corpus has no
adjudicated val/test yet): the flags below were carried over from
`train_decision_segmenter.py` and one didn't match `opf train`'s actual CLI
(`--seed` doesn't exist; `opf train` only has `--shuffle-seed`), which
`opf train --help` would have caught but no local test could, since no
local environment here has `opf` installed. Fixed; see
`test_run_opf_train_epoch_uses_shuffle_seed_not_seed`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import structlog

from segmenter_dataset.schemas import CheckpointSelection, ExperimentManifest


logger = structlog.get_logger()

REQUIRED_TRAIN_ARTIFACTS = ("train.jsonl", "val.jsonl", "label_space.json")


def _detect_device() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def _load_label_space(path: Path) -> dict:
    label_space = json.loads(path.read_text(encoding="utf-8"))
    names = label_space.get("span_class_names", [])
    if not names or names[0] != "O":
        msg = f"Invalid label space: O must be first in span_class_names (got {names[:3]})"
        raise ValueError(msg)
    return label_space


def _run_opf_train_epoch(
    train_jsonl: Path,
    val_jsonl: Path,
    label_space_json: Path,
    epoch_dir: Path,
    *,
    resume_from: Path | None,
    batch_size: int,
    seed: int,
    device: str,
) -> int:
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
        str(epoch_dir),
        "--device",
        device,
        "--epochs",
        "1",
        "--batch-size",
        str(batch_size),
        "--shuffle-seed",
        str(seed),
    ]
    if resume_from is not None:
        cmd += ["--checkpoint", str(resume_from)]
    logger.info("opf_train_epoch_start", cmd=" ".join(cmd))
    result = subprocess.run(cmd, check=False)
    logger.info("opf_train_epoch_done", returncode=result.returncode)
    return result.returncode


def _run_opf_eval(
    jsonl_path: Path, checkpoint_dir: Path, metrics_output: Path, device: str
) -> dict | None:
    """Run `opf eval`. Caller is responsible for never pointing this at test.jsonl."""
    metrics_output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "opf",
        "eval",
        str(jsonl_path),
        "--checkpoint",
        str(checkpoint_dir),
        "--device",
        device,
        "--per-class",
        "--metrics-out",
        str(metrics_output),
    ]
    logger.info("opf_eval_start", cmd=" ".join(cmd), target=str(jsonl_path))
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0 or not metrics_output.exists():
        return None
    try:
        return json.loads(metrics_output.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return None


def _macro_f1_from_metrics(metrics: dict, categories: list[str]) -> float:
    """Mean of per-class span F1 over trainable categories (RFC 0012 §5 point 5's metric)."""
    f1s = []
    for category in categories:
        f1 = metrics.get(f"by_class.{category}.span.f1")
        if f1 is None:
            category_metrics = metrics.get(category, {})
            f1 = category_metrics.get("f1-score") if category_metrics else None
        if f1 is not None:
            f1s.append(f1)
    return sum(f1s) / len(f1s) if f1s else 0.0


@dataclass(frozen=True)
class _EpochResult:
    epoch: int
    macro_f1: float
    val_loss: float | None
    checkpoint_dir: Path


def _select_best_epoch(results: list[_EpochResult]) -> _EpochResult:
    """RFC 0012 §5 point 5: highest val macro-F1; tie -> lowest epoch; tie -> lowest val loss."""

    def sort_key(result: _EpochResult) -> tuple[float, int, float]:
        loss = result.val_loss if result.val_loss is not None else float("inf")
        return (-result.macro_f1, result.epoch, loss)

    return min(results, key=sort_key)


def train_and_select_checkpoint(
    data_dir: Path,
    output_dir: Path,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    device: str,
) -> tuple[CheckpointSelection, Path]:
    """Train epoch-by-epoch, evaluating ONLY on val.jsonl; return the winning checkpoint.

    Never opens `data_dir / "test.jsonl"`, even if present.
    """
    train_jsonl = data_dir / "train.jsonl"
    val_jsonl = data_dir / "val.jsonl"
    label_space_json = data_dir / "label_space.json"
    label_space = _load_label_space(label_space_json)
    categories = [c for c in label_space["span_class_names"] if c != "O"]

    results: list[_EpochResult] = []
    resume_from: Path | None = None

    for epoch in range(1, epochs + 1):
        epoch_dir = output_dir / f"epoch-{epoch}"
        returncode = _run_opf_train_epoch(
            train_jsonl,
            val_jsonl,
            label_space_json,
            epoch_dir,
            resume_from=resume_from,
            batch_size=batch_size,
            seed=seed,
            device=device,
        )
        if returncode != 0:
            msg = f"opf train failed at epoch {epoch} (returncode {returncode})"
            raise RuntimeError(msg)

        metrics_path = output_dir / f"val_metrics_epoch_{epoch}.json"
        metrics = _run_opf_eval(val_jsonl, epoch_dir, metrics_path, device)
        if metrics is None:
            msg = f"opf eval on val.jsonl failed at epoch {epoch}"
            raise RuntimeError(msg)

        macro = _macro_f1_from_metrics(metrics, categories)
        val_loss = metrics.get("loss")
        logger.info("epoch_val_macro_f1", epoch=epoch, macro_f1=macro, val_loss=val_loss)
        results.append(
            _EpochResult(epoch=epoch, macro_f1=macro, val_loss=val_loss, checkpoint_dir=epoch_dir)
        )
        resume_from = epoch_dir

    if not results:
        msg = "no epochs completed"
        raise RuntimeError(msg)

    best = _select_best_epoch(results)
    selection = CheckpointSelection(
        selected_epoch=best.epoch,
        val_macro_f1=best.macro_f1,
        val_loss=best.val_loss,
        per_epoch_val_macro_f1={result.epoch: result.macro_f1 for result in results},
    )
    return selection, best.checkpoint_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train the CausaGanha segmenter baseline (train+val only, RFC 0012 §13)"
    )
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--ontology-version", required=True)
    parser.add_argument("--guideline-version", required=True)
    parser.add_argument("--dependency-lock-hash", required=True, help="sha256 hex of the lockfile")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--device", default=None, help="cuda|cpu; default: auto-detect")
    parser.add_argument("--experiment-id", default=None)
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)

    missing = [name for name in REQUIRED_TRAIN_ARTIFACTS if not (data_dir / name).exists()]
    if missing:
        print(
            f"Error: missing {missing} in {data_dir}. "
            "Run segmenter_dataset.opf_export.export_release_for_training first.",
            file=sys.stderr,
        )
        return 1

    device = args.device or _detect_device()
    selection, checkpoint_dir = train_and_select_checkpoint(
        data_dir,
        output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        seed=args.seed,
        device=device,
    )

    timestamp = datetime.now(UTC)
    experiment_id = args.experiment_id or f"{args.release_id}-train-{timestamp:%Y%m%dT%H%M%SZ}"
    manifest = ExperimentManifest(
        experiment_id=experiment_id,
        release_id=args.release_id,
        ontology_version=args.ontology_version,
        guideline_version=args.guideline_version,
        seed=args.seed,
        dependency_lock_hash=args.dependency_lock_hash,
        epochs=args.epochs,
        batch_size=args.batch_size,
        device=device,
        checkpoint_dir=str(checkpoint_dir),
        checkpoint_selection=selection,
        created_at=timestamp.isoformat(),
    )
    manifest_path = output_dir / "experiment_manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2) + "\n", encoding="utf-8")

    print(f"Selected epoch {selection.selected_epoch} (val macro-F1={selection.val_macro_f1:.3f})")
    print(f"Checkpoint: {checkpoint_dir}")
    print(f"Experiment manifest: {manifest_path}")
    print("\ntest.jsonl was not read by this script.")
    print("To evaluate against the locked test set (exactly once), run:")
    print(
        f"  uv run python scripts/run_segmenter_test_eval.py --experiment-manifest {manifest_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
