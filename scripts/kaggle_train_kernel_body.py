"""Kaggle-specific body of the training kernel — NOT run directly.

scripts/train_on_kaggle.sh generates the actual pushed kernel script by
concatenating, in order: (1) the literal current content of opf_shared.py,
(2) a CONFIG block of literal values (epochs, batch, commits, ...) — Kaggle's
push API has no environment-variable channel, `request.text` (the script
source) is the only place per-run config can travel — and (3) this file's
body, with the `from opf_shared import ...` marker line stripped (opf_shared's
names are already in scope after step 1; this import exists so this file
lints/type-checks on its own, and to make the dependency explicit to a
reader).

Train+eval orchestration, opf command construction, and macro-F1 all live in
opf_shared.py (shared with colab_train_driver.py and
train_decision_segmenter.py) — this file is only Kaggle glue: locate the
mounted dataset, read the optional W&B secret via kaggle_secrets, package
outputs into /kaggle/working (Kaggle's automatic output directory — no
directory-download restriction here, unlike Colab).
"""

# The next two lines are stripped by train_on_kaggle.sh at concat time (marker:
# KAGGLE_STRIP_THIS_LINE) — opf_shared.py's own `from __future__` survives as
# the file's real first statement (a second one after concatenation is a hard
# SyntaxError, verified against the actual generated file, not just this one).
from __future__ import annotations  # KAGGLE_STRIP_THIS_LINE

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from opf_shared import compute_macro_f1, train_and_eval  # KAGGLE_STRIP_THIS_LINE


# --- CONFIG (normally injected above this line by train_on_kaggle.sh) -----
# Fallback values so this file is independently syntax-checkable; the real
# run always has these overwritten by the generated CONFIG block.
DATASET_SLUG = globals().get("DATASET_SLUG", "causaganha-segmenter-splits")
DATASET_OWNER = globals().get("DATASET_OWNER", "unknown")
EPOCHS = globals().get("EPOCHS", 1)
BATCH = globals().get("BATCH", 1)
GPU = globals().get("GPU", "NvidiaTeslaT4")
JOB_TYPE = globals().get("JOB_TYPE", "smoke-test")
OPF_COMMIT = globals().get("OPF_COMMIT", "unknown")
REPO_COMMIT = globals().get("REPO_COMMIT", "unknown")
WANDB_VERSION_PIN = globals().get("WANDB_VERSION_PIN", "0.28.0")
# ---------------------------------------------------------------------------

# Verified live (a diagnostic os.listdir kernel), NOT the flat
# /kaggle/input/<slug>/ path an earlier draft assumed: attached datasets
# mount under /kaggle/input/datasets/<owner>/<slug>/.
DATA = Path("/kaggle/input/datasets") / DATASET_OWNER / DATASET_SLUG
OUT = Path("/kaggle/working")
# dict(os.environ, ...), NOT a bare dict: subprocess.Popen's env= REPLACES the
# whole environment rather than merging, which would have stripped PATH, CUDA
# library paths, HF cache config, etc. (real bug, caught in review — the Colab
# driver already did this correctly; this file didn't).
_ENV = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")


def _install_pinned_deps() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            f"opf @ git+https://github.com/openai/privacy-filter.git@{OPF_COMMIT}",
            f"wandb=={WANDB_VERSION_PIN}",
        ],
        check=True,
    )
    # wandb is always installed (small package) — whether a Secret is actually
    # attached can't be known before the kernel runs, so _get_wandb_key()
    # decides at runtime whether tracking activates, not this install step.


def _get_wandb_key() -> str | None:
    """Read WANDB_API_KEY from a Kaggle Secret attached to this kernel.

    One-time manual setup required (Kaggle has no CLI for attaching secrets):
    kernel editor -> Add-ons -> Secrets -> add WANDB_API_KEY -> attach to this
    kernel. Returns None if kaggle_secrets is unavailable (local dev) or the
    secret isn't attached — training still runs, just without tracking.
    """
    try:
        from kaggle_secrets import UserSecretsClient  # noqa: PLC0415

        return UserSecretsClient().get_secret("WANDB_API_KEY")
    except Exception:
        return None


def _init_run():
    key = _get_wandb_key()
    if not key:
        print("No WANDB_API_KEY secret attached — skipping tracking.")
        return None

    import wandb  # noqa: PLC0415

    wandb.login(key=key)
    input_hashes = {}
    for name in ("train.jsonl", "val.jsonl", "test.jsonl", "label_space.json"):
        import hashlib  # noqa: PLC0415

        h = hashlib.sha256()
        with (DATA / name).open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        input_hashes[name] = h.hexdigest()

    return wandb.init(
        project="causaganha-segmenter",
        job_type=JOB_TYPE,
        config={
            "provider": "kaggle",
            "gpu": GPU,
            "epochs": EPOCHS,
            "batch_size": BATCH,
            "opf_commit": OPF_COMMIT,
            "causaganha_commit": REPO_COMMIT,
            "wandb_version": wandb.__version__,
            "input_sha256": input_hashes,
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

    if report["metrics"] is not None:
        ls = json.loads((DATA / "label_space.json").read_text())
        f1_report = compute_macro_f1(report["metrics"], ls.get("span_class_names", []))
        macro, macro_no_ref = f1_report["macro_f1"], f1_report["macro_f1_no_ref"]
        print(f"macro_f1={macro:.3f} macro_f1_no_ref={macro_no_ref:.3f}")
        if run is not None:
            run.summary.update(
                {
                    "macro_f1": f1_report["macro_f1"],
                    "macro_f1_no_ref": f1_report["macro_f1_no_ref"],
                    "detection_f1": f1_report["detection_f1"],
                    **{f"f1/{cat}": f1 for cat, f1 in f1_report["per_class"].items()},
                }
            )

    # Unlike Colab, Kaggle's own output retrieval handles directories fine —
    # package anyway for a single consistent artifact across both providers.
    shutil.make_archive(str(OUT / "checkpoint"), "gztar", OUT / "best")
    print(f"=== CHECKPOINT PACKAGED: {OUT / 'checkpoint.tar.gz'} ===")
    return 0


def main() -> int:
    _install_pinned_deps()
    run = _init_run()
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
