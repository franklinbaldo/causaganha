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

Invokes `opf train` exactly once, with `--epochs N`, per #1048: OpenAI's
own `openai/privacy-filter/FINETUNING.md` documents one continuous training
process -- AdamW and the epoch shuffle RNG created once and carried across
every epoch, validation evaluated and the best-by-loss state tracked each
epoch, that best state restored before the final checkpoint is written -- as
the canonical custom-label recipe. Re-invoking `opf train --epochs 1`
per epoch (the pre-#1048 design) resets that optimizer/RNG state between
epochs and diverges from the canonical semantics; it is not a co-equal
alternative. This wrapper's job is provenance, artifact transport and
model-agnostic evaluation on top of that canonical run -- not its own
epoch-level orchestration or checkpoint selection, both of which OPF already
does internally by validation loss.

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

`experiment_manifest.json` also records provenance #1048 asks for that this
script can gather on its own, without depending on a new required CLI flag
another caller (the GitHub Actions -> Kaggle runner in the blog repo) would
also have to be updated to pass: `opf --version`'s output, the actual
hardware a `--device cuda` run executed on, a sha256 over the exact
`train.jsonl`/`val.jsonl`/`label_space.json` bytes consumed (tying the
manifest to what was actually trained on, not just to a `--release-id`
string that could point at a rebuilt export), and a copy of the selected
checkpoint's own `finetune_summary.json` when OPF produced one. None of
these are preconditions for training to proceed; each degrades to `None`
independently rather than failing the run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import structlog

from segmenter_dataset.schemas import CheckpointSelection, ExperimentManifest


logger = structlog.get_logger()

REQUIRED_TRAIN_ARTIFACTS = ("train.jsonl", "val.jsonl", "label_space.json")

# #1048: the first serious baseline starts from the upstream openai/privacy-filter
# custom-label fine-tuning demo's recipe, not from OPF's own conservative built-in
# defaults (lr=1e-5, wd=0.01 -- see docs/kaggle-colab-gpu-workflow.md). Leaving
# these flags unpassed silently falls back to that conservative recipe.
DEFAULT_LEARNING_RATE = 2e-4
DEFAULT_WEIGHT_DECAY = 0.0
DEFAULT_GRAD_ACCUM_STEPS = 1
DEFAULT_MAX_GRAD_NORM = 1.0


def _detect_device() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def _detect_opf_version() -> str | None:
    """Best-effort `opf --version`, never fatal -- provenance, not a precondition (#1048)."""
    cmd = [sys.executable, "-m", "opf", "--version"]
    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)  # noqa: S603
    except OSError:
        return None
    if result.returncode != 0:
        return None
    version = result.stdout.strip() or result.stderr.strip()
    return version or None


def _detect_hardware(device: str) -> str:
    """The actual GPU model for a cuda run, falling back to the device string (#1048)."""
    if device != "cuda":
        return device
    try:
        import torch

        return torch.cuda.get_device_name(0)
    except (ImportError, RuntimeError):
        return device


def _hash_dataset_export(data_dir: Path) -> str:
    """sha256 over train/val/label_space bytes, in `REQUIRED_TRAIN_ARTIFACTS` order.

    Ties an experiment manifest to the exact bytes consumed for training,
    rather than to a `--release-id` string that could point at a rebuilt
    export with different content (#1048's "dataset release hash").
    """
    digest = hashlib.sha256()
    for name in REQUIRED_TRAIN_ARTIFACTS:
        digest.update((data_dir / name).read_bytes())
    return digest.hexdigest()


def _preserve_finetune_summary(checkpoint_dir: Path, output_dir: Path) -> str | None:
    """Copy the selected checkpoint's `finetune_summary.json` next to the experiment manifest.

    Returns ``None`` without erroring when OPF didn't produce one -- callers
    must not fail an otherwise-successful run over missing-but-optional
    provenance (#1048).
    """
    source = checkpoint_dir / "finetune_summary.json"
    if not source.exists():
        return None
    destination = output_dir / "finetune_summary.json"
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return str(destination)


def _load_label_space(path: Path) -> dict:
    label_space = json.loads(path.read_text(encoding="utf-8"))
    names = label_space.get("span_class_names", [])
    if not names or names[0] != "O":
        msg = f"Invalid label space: O must be first in span_class_names (got {names[:3]})"
        raise ValueError(msg)
    return label_space


def _run_opf_train(
    train_jsonl: Path,
    val_jsonl: Path,
    label_space_json: Path,
    output_dir: Path,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    device: str,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    weight_decay: float = DEFAULT_WEIGHT_DECAY,
    grad_accum_steps: int = DEFAULT_GRAD_ACCUM_STEPS,
    max_grad_norm: float = DEFAULT_MAX_GRAD_NORM,
) -> int:
    """One continuous `opf train --epochs N` invocation -- the canonical path (#1048).

    No `--checkpoint`/resume flag: unlike the pre-#1048 per-epoch loop, this
    is a single process for the whole run, so there is nothing to hand off
    between calls. Every optimization knob is passed explicitly rather than
    left to `opf train`'s own defaults, so the invocation is reproducible
    from its recorded command alone.
    """
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
        "--grad-accum-steps",
        str(grad_accum_steps),
        "--learning-rate",
        str(learning_rate),
        "--weight-decay",
        str(weight_decay),
        "--max-grad-norm",
        str(max_grad_norm),
        "--shuffle-seed",
        str(seed),
    ]
    logger.info("opf_train_start", cmd=" ".join(cmd), epochs=epochs)
    result = subprocess.run(cmd, check=False)
    logger.info("opf_train_done", returncode=result.returncode)
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


def _metric_payload(metrics: dict) -> dict:
    """Return the metric map from either historical flat or current OPF output.

    Current ``opf eval --metrics-out`` writes an envelope with ``args``,
    ``config``, ``metrics`` and ``summary``. Older experiments/tests used the
    metric keys at the document root, so accept both without weakening the
    caller's contract.
    """
    nested = metrics.get("metrics")
    return nested if isinstance(nested, dict) else metrics


def _macro_f1_from_metrics(metrics: dict, categories: list[str]) -> float:
    """Mean of per-class span F1 over trainable categories (RFC 0012 §5 point 5's metric).

    Every category in ``categories`` counts in the denominator, even one OPF's
    report omits entirely (e.g. zero predictions, or zero recall with no F1
    field emitted) -- excluding it instead would silently inflate macro-F1 by
    averaging only over the categories the model happened to report on (#1048).
    """
    payload = _metric_payload(metrics)
    f1s = []
    for category in categories:
        f1 = payload.get(f"by_class.{category}.span.f1")
        if f1 is None:
            category_metrics = payload.get(category, {})
            f1 = category_metrics.get("f1-score") if category_metrics else None
        f1s.append(f1 if f1 is not None else 0.0)
    return sum(f1s) / len(f1s) if f1s else 0.0


def _validation_loss_from_metrics(metrics: dict) -> float | None:
    """Extract validation loss from historical flat or current OPF output."""
    loss = _metric_payload(metrics).get("loss")
    if isinstance(loss, (int, float)):
        return float(loss)
    return None


def train_and_select_checkpoint(
    data_dir: Path,
    output_dir: Path,
    *,
    epochs: int,
    batch_size: int,
    seed: int,
    device: str,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    weight_decay: float = DEFAULT_WEIGHT_DECAY,
    grad_accum_steps: int = DEFAULT_GRAD_ACCUM_STEPS,
    max_grad_norm: float = DEFAULT_MAX_GRAD_NORM,
) -> tuple[CheckpointSelection, Path]:
    """Run the canonical `opf train --epochs N` once; evaluate the result on val.jsonl (#1048).

    No epoch-level orchestration or checkpoint comparison here: OPF already
    tracks the best-by-validation-loss state across epochs internally and
    restores it before writing the checkpoint (see module docstring). This
    function's only job is to report that checkpoint's validation macro-F1
    as external context. Never opens `data_dir / "test.jsonl"`, even if
    present.
    """
    train_jsonl = data_dir / "train.jsonl"
    val_jsonl = data_dir / "val.jsonl"
    label_space_json = data_dir / "label_space.json"
    label_space = _load_label_space(label_space_json)
    categories = [c for c in label_space["span_class_names"] if c != "O"]

    checkpoint_dir = output_dir / "checkpoint"
    returncode = _run_opf_train(
        train_jsonl,
        val_jsonl,
        label_space_json,
        checkpoint_dir,
        epochs=epochs,
        batch_size=batch_size,
        seed=seed,
        device=device,
        learning_rate=learning_rate,
        weight_decay=weight_decay,
        grad_accum_steps=grad_accum_steps,
        max_grad_norm=max_grad_norm,
    )
    if returncode != 0:
        msg = f"opf train failed (returncode {returncode})"
        raise RuntimeError(msg)

    metrics_path = output_dir / "val_metrics.json"
    metrics = _run_opf_eval(val_jsonl, checkpoint_dir, metrics_path, device)
    if metrics is None:
        msg = "opf eval on val.jsonl failed"
        raise RuntimeError(msg)

    macro = _macro_f1_from_metrics(metrics, categories)
    val_loss = _validation_loss_from_metrics(metrics)
    logger.info("train_val_macro_f1", epochs=epochs, macro_f1=macro, val_loss=val_loss)

    selection = CheckpointSelection(
        selected_epoch=epochs,
        val_macro_f1=macro,
        val_loss=val_loss,
    )
    return selection, checkpoint_dir


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
    parser.add_argument("--learning-rate", type=float, default=DEFAULT_LEARNING_RATE)
    parser.add_argument("--weight-decay", type=float, default=DEFAULT_WEIGHT_DECAY)
    parser.add_argument("--grad-accum-steps", type=int, default=DEFAULT_GRAD_ACCUM_STEPS)
    parser.add_argument("--max-grad-norm", type=float, default=DEFAULT_MAX_GRAD_NORM)
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
    opf_version = _detect_opf_version()
    hardware = _detect_hardware(device)
    selection, checkpoint_dir = train_and_select_checkpoint(
        data_dir,
        output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        seed=args.seed,
        device=device,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        grad_accum_steps=args.grad_accum_steps,
        max_grad_norm=args.max_grad_norm,
    )
    dataset_export_hash = _hash_dataset_export(data_dir)
    finetune_summary_path = _preserve_finetune_summary(checkpoint_dir, output_dir)

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
        dataset_export_hash=dataset_export_hash,
        opf_version=opf_version,
        hardware=hardware,
        finetune_summary_path=finetune_summary_path,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        grad_accum_steps=args.grad_accum_steps,
        max_grad_norm=args.max_grad_norm,
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
