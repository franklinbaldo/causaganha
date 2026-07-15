"""Run opf train + eval on a Colab runtime with W&B observability.

Invoked by ``scripts/train_on_colab.sh`` as a subprocess inside a single
``colab exec``. All config arrives via ``OPF_*`` environment variables set by
the caller, so nothing sensitive is interpolated into a command that gets
echoed. The W&B key is never read here — the caller runs ``wandb login``
first (writes ``~/.netrc``); this driver only calls ``wandb.init``/``log``/
``finish``.

Observability design:
  - the run is created BEFORE training, so a crash still leaves a record;
  - opf's own ``train progress: ... train_loss=N`` stdout (a stable format at
    the PINNED opf commit installed by the caller) is tailed and streamed to
    W&B live;
  - SHA-256 hashes of the four input files, plus the opf commit, causaganha
    commit, and wandb version, go into the run config for data/code lineage;
  - the canonical macro F1 (mean of per-class F1s, via opf_shared) is logged
    to the run summary after eval;
  - training failure fires ``run.alert``; the run is always closed with the
    real exit code in a ``finally`` block.

Exit status: ``main() -> int`` and ``raise SystemExit(main())`` — the caller
reads the printed ``=== DRIVER EXIT CODE: N ===`` marker because a Colab cell
exception does NOT reliably surface as a nonzero ``colab exec`` exit
(observed empirically; see train_on_colab.sh).

On success, the checkpoint directory is packaged as ``checkpoint.tar.gz``
because ``colab download`` refuses directories (IsADirectoryError in
colab_cli's ContentsClient).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from opf_shared import build_opf_eval_cmd, build_opf_train_cmd, compute_macro_f1


DATA = Path(os.environ["OPF_DATA"])
OUT = Path(os.environ["OPF_OUT"])
EPOCHS = int(os.environ.get("OPF_EPOCHS", "1"))
BATCH = int(os.environ.get("OPF_BATCH", "1"))
GPU = os.environ.get("OPF_GPU", "unknown")
JOB_TYPE = os.environ.get("OPF_JOB_TYPE", "smoke-test")
USE_WANDB = os.environ.get("OPF_WANDB", "0") == "1"
OPF_COMMIT = os.environ.get("OPF_PIN_COMMIT", "unknown")
REPO_COMMIT = os.environ.get("OPF_REPO_COMMIT", "unknown")

INPUT_FILES = ("train.jsonl", "val.jsonl", "test.jsonl", "label_space.json")

# expandable_segments reclaims fragmentation headroom — required for opf's full
# fine-tune (1.5B params + full-precision AdamW) to fit a 16GB T4.
_ENV = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")

# opf/_train/runner.py prints these two shapes; both carry live metrics.
_PROGRESS = re.compile(
    r"train progress: epoch=(\d+)/\d+ .*train_loss=([\d.]+) train_token_accuracy=([\d.]+)"
)
_EPOCH = re.compile(
    r"epoch (\d+)/\d+: train_loss=([\d.]+) val_loss=([\d.]+) val_token_accuracy=([\d.]+)"
)


def _run_streamed(cmd: list[str], log_path: Path, on_line=None) -> int:
    """Run cmd, tee stdout+stderr to log_path and the kernel stdout, return rc."""
    with log_path.open("w") as log:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=_ENV
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            log.flush()
            sys.stdout.write(line)
            if on_line is not None:
                on_line(line)
        return proc.wait()


def _make_line_logger(run):
    def on_line(line: str) -> None:
        m = _PROGRESS.search(line)
        if m:
            run.log(
                {
                    "epoch": int(m.group(1)),
                    "train_loss": float(m.group(2)),
                    "train_token_accuracy": float(m.group(3)),
                }
            )
            return
        e = _EPOCH.search(line)
        if e:
            run.log(
                {
                    "epoch": int(e.group(1)),
                    "train_loss": float(e.group(2)),
                    "val_loss": float(e.group(3)),
                    "val_token_accuracy": float(e.group(4)),
                }
            )

    return on_line


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _init_run():
    # Lazy import: wandb is only installed on the runtime when tracking is on.
    import wandb  # noqa: PLC0415

    return wandb.init(
        project="causaganha-segmenter",
        job_type=JOB_TYPE,
        config={
            "gpu": GPU,
            "epochs": EPOCHS,
            "batch_size": BATCH,
            "opf_commit": OPF_COMMIT,
            "causaganha_commit": REPO_COMMIT,
            "wandb_version": wandb.__version__,
            # Data lineage: exact bytes trained on, without uploading a copy.
            "input_sha256": {name: _sha256(DATA / name) for name in INPUT_FILES},
        },
    )


def _train_and_eval(run) -> int:
    ckpt = OUT / "best"
    train_rc = _run_streamed(
        build_opf_train_cmd(
            DATA / "train.jsonl",
            DATA / "val.jsonl",
            DATA / "label_space.json",
            ckpt,
            device="cuda",
            epochs=EPOCHS,
            batch_size=BATCH,
        ),
        OUT / "train.log",
        _make_line_logger(run) if run else None,
    )
    print(f"=== TRAIN EXIT CODE: {train_rc} ===")
    if run is not None:
        run.summary["train_exit_code"] = train_rc
        run.save(str(OUT / "train.log"))
    if train_rc != 0:
        if run is not None:
            run.alert(title="opf train failed", text=f"exit {train_rc} — see train.log")
        return train_rc

    eval_rc = _run_streamed(
        build_opf_eval_cmd(DATA / "test.jsonl", ckpt, OUT / "metrics.json", device="cuda"),
        OUT / "eval.log",
    )
    print(f"=== EVAL EXIT CODE: {eval_rc} ===")
    if run is not None:
        run.summary["eval_exit_code"] = eval_rc
        run.save(str(OUT / "eval.log"))
    if eval_rc != 0:
        if run is not None:
            run.alert(title="opf eval failed", text=f"exit {eval_rc} — see eval.log")
        return eval_rc

    metrics_path = OUT / "metrics.json"
    if metrics_path.exists() and run is not None:
        metrics = json.loads(metrics_path.read_text())
        if isinstance(metrics, dict):
            ls = json.loads((DATA / "label_space.json").read_text())
            report = compute_macro_f1(metrics, ls.get("span_class_names", []))
            run.summary.update(
                {
                    "macro_f1": report["macro_f1"],
                    "macro_f1_no_ref": report["macro_f1_no_ref"],
                    "detection_f1": report["detection_f1"],
                    **{f"f1/{cat}": f1 for cat, f1 in report["per_class"].items()},
                }
            )
        else:
            run.summary["eval_metrics"] = metrics

    # colab download refuses directories — package the checkpoint for retrieval.
    shutil.make_archive(str(OUT / "checkpoint"), "gztar", ckpt)
    print(f"=== CHECKPOINT PACKAGED: {OUT / 'checkpoint.tar.gz'} ===")
    return 0


def main() -> int:
    run = _init_run() if USE_WANDB else None
    rc = 1
    try:
        rc = _train_and_eval(run)
    finally:
        if run is not None:
            print("wandb run:", run.url)
            run.finish(exit_code=rc)
        print(f"=== DRIVER EXIT CODE: {rc} ===")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
