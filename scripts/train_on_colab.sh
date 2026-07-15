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
#   The Colab CLI supports Linux and macOS only — on Windows run everything
#   in WSL2 (its console module imports termios unconditionally; native
#   Windows fails at import).
#
# Optional: W&B run tracking
#   export WANDB_API_KEY=...   # in the shell that runs this script (never echoed)
#   opf itself has no wandb integration (checked README, FINETUNING.md, and a
#   full-repo code search — no report_to/wandb hooks anywhere). If
#   WANDB_API_KEY is set, this script installs wandb on the remote runtime,
#   logs in by uploading the key as a file (not interpolated into any command
#   that gets printed), and the driver streams live metrics + records data/
#   code lineage. If unset, tracking is skipped entirely.
#
# Usage:
#   scripts/train_on_colab.sh --smoke [GPU] [EPOCHS] [BATCH_SIZE]   # seed-pipeline test
#   scripts/train_on_colab.sh [GPU] [EPOCHS] [BATCH_SIZE]           # real run, gates enforced
#   scripts/train_on_colab.sh --smoke              # defaults: T4 1 1
#
# GATING: without --smoke, the readiness gates (G1-G5) are enforced locally
# via `prepare_privacy_filter_dataset.py --check-gates` before any Colab
# session is provisioned. The current seed corpus intentionally fails them —
# use --smoke to test the pipeline itself (T8). --smoke labels the W&B run
# job_type=smoke-test; gated runs are job_type=finetune.
#
# NOTE ON T4 GPU MEMORY (verified empirically, not guessed):
# opf runs a FULL fine-tune of a 1.5B-param model with full-precision AdamW
# (no LoRA / gradient-checkpointing / 8-bit-optimizer flag exists in opf). The
# model + optimizer state + gradients alone consume ~14GB of VRAM — a fixed
# cost independent of batch size. On a T4 (16GB VRAM) this means:
#   - batch_size >= 2 OOMs in the attention forward pass (confirmed).
#   - batch_size=1 + PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True DOES fit
#     and trains through to a checkpoint (confirmed: train_loss ~0.81,
#     val_token_accuracy ~0.93 on the smoke set). The driver sets that env var.
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
#   1. enforces the readiness gates locally (unless --smoke)
#   2. provisions a uniquely named GPU session
#   3. installs PINNED deps on the runtime (opf commit + wandb version below)
#   4. uploads the frozen artifact set (data/segmenter_splits/*)
#   5. if WANDB_API_KEY is set: installs wandb + logs in on the runtime
#   6. uploads and runs colab_train_driver.py + opf_shared.py, which train +
#      eval via the same command construction as train_decision_segmenter.py,
#      stream live train_loss to W&B, record input hashes + commits in the run
#      config, and package the checkpoint as a tarball — see those files
#   7. verifies the driver's real exit code (a Colab cell exception does NOT
#      reliably make `colab exec` exit nonzero — observed empirically — so the
#      driver prints an explicit "=== DRIVER EXIT CODE: N ===" marker that
#      this script parses)
#   8. downloads checkpoint.tar.gz (colab download refuses directories),
#      extracts it, then tears the session down

set -euo pipefail

# --- pinned remote environment (bump deliberately, together with a re-test) --
OPF_PIN_COMMIT="f7f00ca7fb869683eb732c010299d901457f19c3"  # openai/privacy-filter main, 2026-07-15
WANDB_PIN="0.28.0"

SMOKE=0
if [[ "${1:-}" == "--smoke" ]]; then
  SMOKE=1
  shift
fi

GPU="${1:-T4}"
EPOCHS="${2:-1}"
BATCH_SIZE="${3:-1}"
SESSION="seg-train-$(date +%s)"
DATA_DIR="data/segmenter_splits"
OUT_DIR="models/decision_segmenter"
REMOTE_DATA="/content/data"
REMOTE_OUT="/content/out"
SCRIPT_DIR="$(dirname "$0")"

command -v colab >/dev/null || {
  echo "colab CLI not found. Install with: uv tool install google-colab-cli (WSL2 on Windows)" >&2
  exit 1
}

for f in train.jsonl val.jsonl test.jsonl label_space.json; do
  [[ -f "$DATA_DIR/$f" ]] || { echo "missing $DATA_DIR/$f" >&2; exit 1; }
done

if [[ "$SMOKE" == "1" ]]; then
  JOB_TYPE="smoke-test"
  echo "==> --smoke: readiness gates bypassed (seed-pipeline test, W&B job_type=smoke-test)"
else
  JOB_TYPE="finetune"
  echo "==> enforcing readiness gates (G1-G5) on $DATA_DIR"
  # Caveat: `uv run` builds the project; under WSL2 on a /mnt/c checkout the
  # editable build can fail on a DrvFs permission quirk (egg-info temp file).
  # If that bites, run the gate check once from Windows or a Linux-native
  # clone — the gates read only the split files, nothing machine-specific.
  if ! uv run python scripts/prepare_privacy_filter_dataset.py --check-gates --gold-dir "$DATA_DIR"; then
    echo "" >&2
    echo "Readiness gates failed: the corpus is not fit for a real training run." >&2
    echo "To test the pipeline itself on the seed data, re-run with --smoke." >&2
    exit 1
  fi
fi

REPO_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

WANDB_KEY_TMP=""
cleanup() {
  # The key-bearing temp file must not survive a failure between mktemp and rm.
  [[ -n "$WANDB_KEY_TMP" ]] && rm -f "$WANDB_KEY_TMP"
  echo "==> stopping session"
  colab stop -s "$SESSION" || true
}

echo "==> provisioning $GPU session '$SESSION'"
colab new -s "$SESSION" --gpu "$GPU"
trap cleanup EXIT

echo "==> installing pinned deps on the runtime (opf@${OPF_PIN_COMMIT:0:8})"
# --timeout: colab exec defaults to 30s; installing opf from git + importing
# torch takes longer, and a 30s cap surfaces as "RuntimeError: Connection was
# lost" mid-op. Every long-running exec below sets an explicit timeout.
colab exec -s "$SESSION" --timeout 300 <<PY
import subprocess, sys
subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                "opf @ git+https://github.com/openai/privacy-filter.git@$OPF_PIN_COMMIT"],
               check=True)
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
  echo "==> configuring wandb ($WANDB_PIN) on the runtime"
  WANDB_KEY_TMP="$(mktemp)"
  printf '%s' "$WANDB_API_KEY" > "$WANDB_KEY_TMP"
  colab upload -s "$SESSION" "$WANDB_KEY_TMP" "/content/.wandb_key"
  rm -f "$WANDB_KEY_TMP"
  WANDB_KEY_TMP=""
  colab exec -s "$SESSION" --timeout 120 <<PY
import subprocess, sys, os
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "wandb==$WANDB_PIN"], check=True)
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

echo "==> uploading training driver + shared module"
colab upload -s "$SESSION" "$SCRIPT_DIR/colab_train_driver.py" "/content/colab_train_driver.py"
colab upload -s "$SESSION" "$SCRIPT_DIR/opf_shared.py" "/content/opf_shared.py"

echo "==> training + evaluating (epochs=$EPOCHS batch=$BATCH_SIZE, wandb=$USE_WANDB, job=$JOB_TYPE)"
# One exec runs colab_train_driver.py as a subprocess (clean process, no
# globals echoed by the kernel). Config via OPF_* env vars — no secret is
# interpolated (wandb auth is in ~/.netrc from `wandb login` above).
# --timeout 1800: train+eval in one exec; the 30s default would guillotine it.
# The exec output is captured because a cell exception does NOT reliably make
# `colab exec` exit nonzero — the driver's printed exit-code marker is the
# reliable signal, verified below.
DRIVER_LOG="$(mktemp)"
colab exec -s "$SESSION" --timeout 1800 <<PY | tee "$DRIVER_LOG"
import os, subprocess, sys
env = dict(os.environ,
           OPF_DATA="$REMOTE_DATA", OPF_OUT="$REMOTE_OUT",
           OPF_EPOCHS="$EPOCHS", OPF_BATCH="$BATCH_SIZE",
           OPF_GPU="$GPU", OPF_WANDB="$USE_WANDB", OPF_JOB_TYPE="$JOB_TYPE",
           OPF_PIN_COMMIT="$OPF_PIN_COMMIT", OPF_REPO_COMMIT="$REPO_COMMIT",
           PYTHONPATH="/content")
subprocess.run([sys.executable, "/content/colab_train_driver.py"],
               env=env, check=False)
PY

if ! grep -q "=== DRIVER EXIT CODE: 0 ===" "$DRIVER_LOG"; then
  rm -f "$DRIVER_LOG"
  echo "" >&2
  echo "Training driver did not report success — see output above." >&2
  exit 1
fi
rm -f "$DRIVER_LOG"

echo "==> downloading logs, metrics and checkpoint tarball"
mkdir -p "$OUT_DIR"
colab download -s "$SESSION" "$REMOTE_OUT/train.log" "$OUT_DIR/train.log" || true
colab download -s "$SESSION" "$REMOTE_OUT/eval.log" "$OUT_DIR/eval.log" || true
colab download -s "$SESSION" "$REMOTE_OUT/metrics.json" "$OUT_DIR/metrics.json"
colab download -s "$SESSION" "$REMOTE_OUT/checkpoint.tar.gz" "$OUT_DIR/checkpoint.tar.gz"

echo "==> extracting checkpoint"
rm -rf "$OUT_DIR/best"
mkdir -p "$OUT_DIR/best"
tar -xzf "$OUT_DIR/checkpoint.tar.gz" -C "$OUT_DIR/best"

echo "==> done: $OUT_DIR/best + $OUT_DIR/metrics.json"
