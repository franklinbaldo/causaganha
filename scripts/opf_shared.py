"""Shared opf command construction, run orchestration, and metric reporting.

Single source of truth for how CausaGanha invokes ``opf train`` / ``opf eval``,
how a run is streamed + logged, and how the canonical macro F1 is computed
from opf's metrics JSON. Used by the local runner
(``train_decision_segmenter.py``) and every remote-GPU driver (Colab's
``colab_train_driver.py``, Kaggle's ``kaggle_train_kernel.py``) so a CLI
change, a metric correction, or a bugfix in the run loop is made ONCE.

STDLIB-ONLY on purpose: remote drivers upload/inline this file onto a bare
runtime where no repo dependency (structlog, torch, ibis) is installed.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from collections.abc import Callable
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


def run_streamed(
    cmd: list[str], log_path: Path, env: dict, on_line: Callable[[str], None] | None = None
) -> int:
    """Run cmd, tee stdout+stderr to log_path and this process's stdout.

    ``on_line`` is called with each raw line as it arrives (e.g. to parse
    opf's progress output and stream it to a tracker) — see
    ``opf_progress_line``.
    """
    with log_path.open("w") as log:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            log.flush()
            sys.stdout.write(line)
            if on_line is not None:
                on_line(line)
        return proc.wait()


# opf/_train/runner.py prints these two shapes; both carry live metrics. Valid
# at the pinned opf commit each driver installs — re-verify against
# `train progress:` / per-epoch summary lines if the pin is bumped.
_PROGRESS_RE = re.compile(
    r"train progress: epoch=(\d+)/\d+ .*train_loss=([\d.]+) train_token_accuracy=([\d.]+)"
)
_EPOCH_RE = re.compile(
    r"epoch (\d+)/\d+: train_loss=([\d.]+) val_loss=([\d.]+) val_token_accuracy=([\d.]+)"
)


def parse_opf_progress_line(line: str) -> dict | None:
    """Extract live metrics from one line of opf train's stdout, or None."""
    m = _PROGRESS_RE.search(line)
    if m:
        return {
            "epoch": int(m.group(1)),
            "train_loss": float(m.group(2)),
            "train_token_accuracy": float(m.group(3)),
        }
    e = _EPOCH_RE.search(line)
    if e:
        return {
            "epoch": int(e.group(1)),
            "train_loss": float(e.group(2)),
            "val_loss": float(e.group(3)),
            "val_token_accuracy": float(e.group(4)),
        }
    return None


def train_and_eval(
    data_dir: Path,
    out_dir: Path,
    *,
    device: str,
    epochs: int,
    batch_size: int,
    env: dict,
    on_metric: Callable[[dict], None] | None = None,
) -> dict:
    """Run opf train then eval; return a report dict, never raises on opf failure.

    ``env`` is the subprocess environment (callers set
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True — required for opf to fit
    a 16GB T4, see train_on_colab.sh). ``on_metric`` is called with each parsed
    live metric dict during training (e.g. to stream to a tracker).

    Returns ``{"train_rc": int, "eval_rc": int | None, "metrics": dict | None}``.
    ``eval_rc``/``metrics`` are None if training failed (no checkpoint exists).
    """
    ckpt = out_dir / "best"

    def _on_line(line: str) -> None:
        if on_metric is not None:
            parsed = parse_opf_progress_line(line)
            if parsed is not None:
                on_metric(parsed)

    train_rc = run_streamed(
        build_opf_train_cmd(
            data_dir / "train.jsonl",
            data_dir / "val.jsonl",
            data_dir / "label_space.json",
            ckpt,
            device=device,
            epochs=epochs,
            batch_size=batch_size,
        ),
        out_dir / "train.log",
        env,
        _on_line,
    )
    print(f"=== TRAIN EXIT CODE: {train_rc} ===")
    if train_rc != 0:
        return {"train_rc": train_rc, "eval_rc": None, "metrics": None}

    eval_rc = run_streamed(
        build_opf_eval_cmd(data_dir / "test.jsonl", ckpt, out_dir / "metrics.json", device=device),
        out_dir / "eval.log",
        env,
    )
    print(f"=== EVAL EXIT CODE: {eval_rc} ===")

    metrics = None
    metrics_path = out_dir / "metrics.json"
    if eval_rc == 0 and metrics_path.exists():
        metrics = json.loads(metrics_path.read_text())

    return {"train_rc": train_rc, "eval_rc": eval_rc, "metrics": metrics}


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
