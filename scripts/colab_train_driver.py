"""Run opf train + eval on a Colab runtime with W&B observability.

Invoked by ``scripts/train_on_colab.sh`` as a subprocess inside a single
``colab exec``. All config arrives via ``OPF_*`` environment variables set by
the caller, so nothing sensitive is interpolated into a command that gets
echoed. The W&B key is never read here — the caller runs ``wandb login``
first (writes ``~/.netrc``); this driver only calls ``wandb.init``/``log``/
``finish``.

The actual train+eval loop, command construction, and macro-F1 computation
live in ``opf_shared.py`` (uploaded alongside this file) — shared with the
Kaggle driver (``kaggle_train_kernel.py``) and the local runner
(``train_decision_segmenter.py``) so there is exactly one implementation.
This file is provider glue: W&B lifecycle, data/code lineage, checkpoint
packaging (``colab download`` refuses directories).

Exit status: ``main() -> int`` and ``raise SystemExit(main())`` — the caller
reads the printed ``=== DRIVER EXIT CODE: N ===`` marker because a Colab cell
exception does NOT reliably surface as a nonzero ``colab exec`` exit
(observed empirically; see train_on_colab.sh).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

from opf_shared import compute_macro_f1, train_and_eval


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


def _run(run) -> int:
    report = train_and_eval(
        DATA,
        OUT,
        device="cuda",
        epochs=EPOCHS,
        batch_size=BATCH,
        env=_ENV,
        on_metric=(run.log if run is not None else None),
    )

    if run is not None:
        run.summary["train_exit_code"] = report["train_rc"]
        run.save(str(OUT / "train.log"))

    if report["train_rc"] != 0:
        if run is not None:
            run.alert(title="opf train failed", text=f"exit {report['train_rc']} — see train.log")
        return report["train_rc"]

    if run is not None:
        run.summary["eval_exit_code"] = report["eval_rc"]
        run.save(str(OUT / "eval.log"))

    if report["eval_rc"] != 0:
        if run is not None:
            run.alert(title="opf eval failed", text=f"exit {report['eval_rc']} — see eval.log")
        return report["eval_rc"]

    if report["metrics"] is not None and run is not None:
        ls = json.loads((DATA / "label_space.json").read_text())
        f1_report = compute_macro_f1(report["metrics"], ls.get("span_class_names", []))
        run.summary.update(
            {
                "macro_f1": f1_report["macro_f1"],
                "macro_f1_no_ref": f1_report["macro_f1_no_ref"],
                "detection_f1": f1_report["detection_f1"],
                **{f"f1/{cat}": f1 for cat, f1 in f1_report["per_class"].items()},
            }
        )

    # colab download refuses directories — package the checkpoint for retrieval.
    shutil.make_archive(str(OUT / "checkpoint"), "gztar", OUT / "best")
    print(f"=== CHECKPOINT PACKAGED: {OUT / 'checkpoint.tar.gz'} ===")
    return 0


def main() -> int:
    run = _init_run() if USE_WANDB else None
    rc = 1
    try:
        rc = _run(run)
    finally:
        if run is not None:
            print("wandb run:", run.url)
            run.finish(exit_code=rc)
        print(f"=== DRIVER EXIT CODE: {rc} ===")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
