"""Run opf train + eval on a Colab runtime with live W&B observability.

Invoked by ``scripts/train_on_colab.sh`` from inside a single ``colab exec``.
All config arrives via ``OPF_*`` environment variables set by the caller, so
nothing sensitive is interpolated into a command that gets echoed. The W&B key
is never read here — the caller runs ``wandb login`` first (writes ``~/.netrc``);
this driver only calls ``wandb.init``/``log``/``finish``.

Observability design (vs. the old "log only the final metrics after success"):
  - the run is created BEFORE training, so a crash still leaves a record;
  - opf's own ``train progress: ... train_loss=N`` stdout (emitted every
    ``progress_interval_s``) is tailed and streamed to W&B live;
  - the gold splits are pinned to the run as an Artifact for data lineage;
  - training failure fires ``run.alert`` and closes the run with its exit code.

Failure propagates to bash without ``sys.exit`` (which, inside the Colab kernel,
raised SystemExit and truncated the log): on train failure the checkpoint dir is
never written, so the mandatory checkpoint download in the shell script fails
under ``set -e``.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


DATA = Path(os.environ["OPF_DATA"])
OUT = Path(os.environ["OPF_OUT"])
EPOCHS = os.environ.get("OPF_EPOCHS", "3")
BATCH = os.environ.get("OPF_BATCH", "1")
GPU = os.environ.get("OPF_GPU", "unknown")
JOB_TYPE = os.environ.get("OPF_JOB_TYPE", "smoke-test")
USE_WANDB = os.environ.get("OPF_WANDB", "0") == "1"

# expandable_segments reclaims fragmentation headroom — required for opf's full
# fine-tune (1.5B params + full-precision AdamW) to fit a 16GB T4.
_ENV = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")

# opf/_train/runner.py prints these two shapes; both carry live metrics.
_PROGRESS = re.compile(
    r"train progress: epoch=(\d+)/\d+ .*train_loss=([\d.]+) "
    r"train_token_accuracy=([\d.]+)"
)
_EPOCH = re.compile(
    r"epoch (\d+)/\d+: train_loss=([\d.]+) val_loss=([\d.]+) "
    r"val_token_accuracy=([\d.]+)"
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


def _init_run():
    # Lazy import: wandb is only installed on the runtime when tracking is on.
    import wandb  # noqa: PLC0415

    run = wandb.init(
        project="causaganha-segmenter",
        job_type=JOB_TYPE,
        config={"gpu": GPU, "epochs": int(EPOCHS), "batch_size": int(BATCH)},
    )
    art = wandb.Artifact("gold-splits", type="dataset")
    for name in ("train.jsonl", "val.jsonl", "test.jsonl", "label_space.json"):
        art.add_file(str(DATA / name))
    run.use_artifact(art)
    return run


def main() -> None:
    run = _init_run() if USE_WANDB else None

    train_rc = _run_streamed(
        [
            sys.executable,
            "-m",
            "opf",
            "train",
            str(DATA / "train.jsonl"),
            "--validation-dataset",
            str(DATA / "val.jsonl"),
            "--label-space-json",
            str(DATA / "label_space.json"),
            "--output-dir",
            str(OUT / "best"),
            "--device",
            "cuda",
            "--epochs",
            EPOCHS,
            "--batch-size",
            BATCH,
        ],
        OUT / "train.log",
        _make_line_logger(run) if run else None,
    )
    print(f"=== TRAIN EXIT CODE: {train_rc} ===")

    if train_rc != 0:
        # No checkpoint was produced; the shell script's checkpoint download will
        # fail and stop the run under set -e. Record the failure in W&B first.
        if run is not None:
            run.summary["train_exit_code"] = train_rc
            run.alert(title="opf train failed", text=f"exit {train_rc} — see train.log")
            run.save(str(OUT / "train.log"))
            run.finish(exit_code=train_rc)
        return

    eval_rc = _run_streamed(
        [
            sys.executable,
            "-m",
            "opf",
            "eval",
            str(DATA / "test.jsonl"),
            "--checkpoint",
            str(OUT / "best"),
            "--device",
            "cuda",
            "--per-class",
            "--metrics-out",
            str(OUT / "metrics.json"),
        ],
        OUT / "eval.log",
    )
    print(f"=== EVAL EXIT CODE: {eval_rc} ===")

    if run is not None:
        metrics_path = OUT / "metrics.json"
        if metrics_path.exists():
            metrics = json.loads(metrics_path.read_text())
            run.summary.update(metrics if isinstance(metrics, dict) else {"eval_metrics": metrics})
        run.summary["eval_exit_code"] = eval_rc
        run.save(str(OUT / "train.log"))
        run.save(str(OUT / "eval.log"))
        print("wandb run:", run.url)
        run.finish(exit_code=eval_rc)


if __name__ == "__main__":
    main()
