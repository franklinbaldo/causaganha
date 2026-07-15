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
#   scripts/train_on_colab.sh T4 3 2           # defaults
#   scripts/train_on_colab.sh A100 5 16
#
# NOTE: opf's base model is a large MoE model (~2.8GB checkpoint). batch_size=8
# OOMs on a T4 (16GB) even for the tiny smoke-test dataset. batch_size=2 fits;
# raise it only on a bigger GPU (A100) for real (non-smoke) training runs.
#
# What it does:
#   1. provisions a GPU session named "seg-train"
#   2. installs opf (openai/privacy-filter) on the runtime
#   3. uploads the frozen artifact set (data/segmenter_splits/*)
#   4. runs `opf train` with the v7 label space
#   5. runs `opf eval --per-class` on test.jsonl
#   6. downloads checkpoint + metrics to models/decision_segmenter/
#   7. tears the session down
#
# NOTE: training is gated — run the readiness gates first:
#   uv run python scripts/prepare_privacy_filter_dataset.py  (promote mode)
# A gate failure means the gold corpus is not ready; do not bypass with toy
# runs except to smoke-test the pipeline itself (T8).

set -euo pipefail

GPU="${1:-T4}"
EPOCHS="${2:-3}"
BATCH_SIZE="${3:-2}"
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
colab exec -s "$SESSION" <<'PY'
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

echo "==> training (epochs=$EPOCHS batch=$BATCH_SIZE)"
colab exec -s "$SESSION" <<PY
import subprocess, sys
with open("$REMOTE_OUT/train.log", "w") as log:
    proc = subprocess.run([sys.executable, "-m", "opf", "train",
                    "$REMOTE_DATA/train.jsonl",
                    "--validation-dataset", "$REMOTE_DATA/val.jsonl",
                    "--label-space-json", "$REMOTE_DATA/label_space.json",
                    "--output-dir", "$REMOTE_OUT/best",
                    "--device", "cuda",
                    "--epochs", "$EPOCHS",
                    "--batch-size", "$BATCH_SIZE"],
                   stdout=log, stderr=subprocess.STDOUT)
print("train exit code:", proc.returncode)
print(open("$REMOTE_OUT/train.log").read()[-4000:])
sys.exit(proc.returncode)
PY

echo "==> evaluating on test split"
colab exec -s "$SESSION" <<PY
import subprocess, sys
with open("$REMOTE_OUT/eval.log", "w") as log:
    proc = subprocess.run([sys.executable, "-m", "opf", "eval",
                    "$REMOTE_DATA/test.jsonl",
                    "--checkpoint", "$REMOTE_OUT/best",
                    "--device", "cuda",
                    "--per-class",
                    "--metrics-out", "$REMOTE_OUT/metrics.json"],
                   stdout=log, stderr=subprocess.STDOUT)
print("eval exit code:", proc.returncode)
print(open("$REMOTE_OUT/eval.log").read()[-4000:])
sys.exit(proc.returncode)
PY

if [[ "$USE_WANDB" == "1" ]]; then
  echo "==> logging results to wandb"
  colab exec -s "$SESSION" <<PY
import json
import wandb

run = wandb.init(project="causaganha-segmenter", job_type="smoke-test",
                  config={"gpu": "$GPU", "epochs": $EPOCHS, "batch_size": $BATCH_SIZE})
try:
    with open("$REMOTE_OUT/metrics.json") as f:
        metrics = json.load(f)
    run.log(metrics if isinstance(metrics, dict) else {"eval_metrics": metrics})
except FileNotFoundError:
    print("no metrics.json to log")
run.save("$REMOTE_OUT/train.log")
run.save("$REMOTE_OUT/eval.log")
print("wandb run:", run.url)
run.finish()
PY
fi

echo "==> downloading checkpoint + metrics"
mkdir -p "$OUT_DIR"
colab download -s "$SESSION" "$REMOTE_OUT/train.log" "$OUT_DIR/train.log" || true
colab download -s "$SESSION" "$REMOTE_OUT/eval.log" "$OUT_DIR/eval.log" || true
colab download -s "$SESSION" "$REMOTE_OUT/best" "$OUT_DIR/best"
colab download -s "$SESSION" "$REMOTE_OUT/metrics.json" "$OUT_DIR/metrics.json"

echo "==> done: $OUT_DIR/best + $OUT_DIR/metrics.json"
