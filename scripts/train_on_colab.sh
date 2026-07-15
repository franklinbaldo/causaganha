#!/usr/bin/env bash
# train_on_colab.sh — drive segmenter training on a Colab GPU from the terminal.
#
# Wraps the Google Colab CLI (https://github.com/googlecolab/google-colab-cli)
# around the same flow as notebooks/train_segmenter_colab.ipynb, so training
# becomes one command instead of a manual notebook session.
#
# Prerequisites (one-time):
#   uv tool install google-colab-cli
#   colab new          # triggers the OAuth browser flow; needs a Google account
#                      # with Colab GPU access (Pro recommended for >T4)
#
# Optional: W&B run tracking
#   export WANDB_API_KEY=...   # in the shell that runs this script (never echoed)
#   opf itself has no wandb integration (checked README, FINETUNING.md, and a
#   full-repo code search — no report_to/wandb hooks anywhere). If
#   WANDB_API_KEY is set, this script installs wandb on the remote runtime,
#   logs in by uploading the key as a file (not interpolated into any command
#   that gets printed), and logs the final eval metrics + train/eval logs as
#   a run after opf finishes. If unset, this step is skipped entirely.
#
# Usage:
#   scripts/train_on_colab.sh [GPU] [EPOCHS] [BATCH_SIZE]
#   scripts/train_on_colab.sh T4 1 1           # defaults
#   scripts/train_on_colab.sh A100 5 16
#
# NOTE ON T4 GPU MEMORY (verified empirically, not guessed):
# opf runs a FULL fine-tune of a 1.5B-param model with full-precision AdamW
# (no LoRA / gradient-checkpointing / 8-bit-optimizer flag exists in opf). The
# model + optimizer state + gradients alone consume ~14GB of VRAM — a fixed
# cost independent of batch size. On a T4 (16GB VRAM) this means:
#   - batch_size >= 2 OOMs in the attention forward pass (confirmed).
#   - batch_size=1 + PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True DOES fit
#     and trains through to a checkpoint (confirmed: train_loss ~0.81,
#     val_token_accuracy ~0.93 on the smoke set). This script sets that env var.
# batch_size is NOT the lever for bigger runs — GPU VRAM is. For real training
# raise the batch only on a bigger GPU (L4 24GB / A100 40GB).
#
# NOTE ON T4 HOST RAM (verified empirically — a SEPARATE ceiling from VRAM):
# Even with the GPU-memory fix above, epochs=3 dies with SIGKILL (-9) partway
# through epoch 2, on HOST RAM (not GPU) — confirmed by sampling /proc/meminfo
# during the run: usage sits ~3GB through epoch 1, then spikes 3GB->12.4GB in
# ~18s right around epoch completion and hits the T4 runtime's ~13GB host-RAM
# ceiling. Ruled out: wandb overhead (still -9 with WANDB_API_KEY unset).
# Suspected but NOT verified: opf's checkpoint-save path (writing a 1.5B-param
# safetensors + optimizer state) may serialize through host RAM. Confirming
# that needs reading opf's save code, not another GPU run. Until fixed or
# understood, default epochs=1, which completes cleanly end-to-end. Multi-epoch
# real training will need either a fix upstream, a high-RAM Colab runtime, or
# per-epoch checkpointing changes — don't raise epochs on a T4 without one of
# those.
#
# What it does:
#   1. provisions a GPU session named "seg-train"
#   2. installs opf (openai/privacy-filter) on the runtime
#   3. uploads the frozen artifact set (data/segmenter_splits/*)
#   4. if WANDB_API_KEY is set: installs wandb + logs in on the runtime
#   5. uploads and runs scripts/colab_train_driver.py, which trains + evals and
#      (when wandb is on) streams live train_loss, pins the gold splits as an
#      artifact, and alerts on failure — see that file
#   6. downloads checkpoint + metrics to models/decision_segmenter/
#   7. tears the session down
#
# NOTE: training is gated — run the readiness gates first:
#   uv run python scripts/prepare_privacy_filter_dataset.py  (promote mode)
# A gate failure means the gold corpus is not ready; do not bypass with toy
# runs except to smoke-test the pipeline itself (T8).

set -euo pipefail

GPU="${1:-T4}"
EPOCHS="${2:-1}"
BATCH_SIZE="${3:-1}"
SESSION="seg-train"
DATA_DIR="data/segmenter_splits"
OUT_DIR="models/decision_segmenter"
REMOTE_DATA="/content/data"
REMOTE_OUT="/content/out"

command -v colab >/dev/null || {
  echo "colab CLI not found. Install with: uv tool install google-colab-cli" >&2
  exit 1
}

for f in train.jsonl val.jsonl test.jsonl label_space.json; do
  [[ -f "$DATA_DIR/$f" ]] || { echo "missing $DATA_DIR/$f" >&2; exit 1; }
done

echo "==> provisioning $GPU session '$SESSION'"
colab new -s "$SESSION" --gpu "$GPU"
trap 'echo "==> stopping session"; colab stop -s "$SESSION" || true' EXIT

echo "==> installing opf on the runtime"
# --timeout: colab exec defaults to 30s; installing opf from git + importing
# torch takes longer, and a 30s cap surfaces as "RuntimeError: Connection was
# lost" mid-op. Every long-running exec below sets an explicit timeout.
colab exec -s "$SESSION" --timeout 300 <<'PY'
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "opf @ git+https://github.com/openai/privacy-filter.git",
                "httpx"], check=True)
import torch
assert torch.cuda.is_available(), "no GPU on runtime"
print("GPU:", torch.cuda.get_device_name(0))
PY

echo "==> preparing remote directories"
colab exec -s "$SESSION" <<PY
import os
os.makedirs("$REMOTE_DATA", exist_ok=True)
os.makedirs("$REMOTE_OUT", exist_ok=True)
PY

echo "==> uploading artifact set"
for f in train.jsonl val.jsonl test.jsonl label_space.json; do
  colab upload -s "$SESSION" "$DATA_DIR/$f" "$REMOTE_DATA/$f"
done

USE_WANDB=0
if [[ -n "${WANDB_API_KEY:-}" ]]; then
  echo "==> configuring wandb on the runtime"
  WANDB_KEY_TMP="$(mktemp)"
  printf '%s' "$WANDB_API_KEY" > "$WANDB_KEY_TMP"
  colab upload -s "$SESSION" "$WANDB_KEY_TMP" "/content/.wandb_key"
  rm -f "$WANDB_KEY_TMP"
  colab exec -s "$SESSION" <<'PY'
import subprocess, sys, os
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "wandb"], check=True)
import wandb
with open("/content/.wandb_key") as f:
    key = f.read().strip()
os.remove("/content/.wandb_key")
wandb.login(key=key)
print("wandb: logged in")
PY
  USE_WANDB=1
else
  echo "==> WANDB_API_KEY not set, skipping wandb (export it before running to enable)"
fi

echo "==> uploading training driver"
colab upload -s "$SESSION" "$(dirname "$0")/colab_train_driver.py" "/content/colab_train_driver.py"

echo "==> training + evaluating (epochs=$EPOCHS batch=$BATCH_SIZE, wandb=$USE_WANDB)"
# One exec runs scripts/colab_train_driver.py, which streams opf's live
# train_loss to W&B, pins the gold splits as an artifact, and alerts on
# failure (see that file). Config is passed as OPF_* env vars — no secret is
# interpolated here (the key is already in ~/.netrc from `wandb login` above).
# --timeout 1800: train+eval in one exec; the 30s default would guillotine it.
colab exec -s "$SESSION" --timeout 1800 <<PY
import os, subprocess, sys
# Run the driver as a subprocess (not runpy) so the kernel doesn't echo the
# module globals dict, and so the driver runs in a clean process. It inherits
# these OPF_* vars via env; wandb auth comes from ~/.netrc.
env = dict(os.environ,
           OPF_DATA="$REMOTE_DATA", OPF_OUT="$REMOTE_OUT",
           OPF_EPOCHS="$EPOCHS", OPF_BATCH="$BATCH_SIZE",
           OPF_GPU="$GPU", OPF_WANDB="$USE_WANDB", OPF_JOB_TYPE="smoke-test")
subprocess.run([sys.executable, "/content/colab_train_driver.py"],
               env=env, check=False)
PY

echo "==> downloading checkpoint + metrics"
mkdir -p "$OUT_DIR"
colab download -s "$SESSION" "$REMOTE_OUT/train.log" "$OUT_DIR/train.log" || true
colab download -s "$SESSION" "$REMOTE_OUT/eval.log" "$OUT_DIR/eval.log" || true
colab download -s "$SESSION" "$REMOTE_OUT/best" "$OUT_DIR/best"
colab download -s "$SESSION" "$REMOTE_OUT/metrics.json" "$OUT_DIR/metrics.json"

echo "==> done: $OUT_DIR/best + $OUT_DIR/metrics.json"
