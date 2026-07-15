#!/usr/bin/env bash
# train_on_kaggle.sh — drive segmenter training on a Kaggle GPU kernel.
#
# Batch-job alternative to scripts/train_on_colab.sh, using the official
# [Kaggle CLI](https://github.com/Kaggle/kaggle-api). Unlike Colab's
# persistent-session model (colab new/exec/upload/download/stop), Kaggle is a
# submit-and-poll batch job: push a script, it runs to completion or error,
# then you pull whatever it wrote to /kaggle/working. No live shell into a
# running kernel — verified against the CLI's own source
# (kaggle_api_extended.py): `kernels_push` reads exactly one `code_file`'s
# text as the ENTIRE kernel payload; there is no upload-arbitrary-file or
# exec-into-session equivalent. Consequences of that, both handled below:
#   - training data must be a Kaggle Dataset (dataset_sources), not an upload
#   - opf_shared.py can't be a sibling import — its literal current content
#     is concatenated into the pushed script at build time (see below), so
#     it stays the single implementation, never hand-duplicated
#
# Prerequisites (one-time):
#   uv tool install kaggle
#   Get an API token: kaggle.com/settings -> Create New Token. Either save it
#   as ~/.kaggle/kaggle.json (chmod 600), or export KAGGLE_KEY (the CLI maps
#   any KAGGLE_* env var to its config directly — verified against source).
#   The account's username is resolved automatically from the token at
#   runtime (verified: the KGAT_-prefixed token format is self-describing) —
#   no separate username variable needed.
#   Optional W&B: Kaggle has no CLI for kernel secrets — attach one manually,
#   once, via the kernel editor: Add-ons -> Secrets -> WANDB_API_KEY. There is
#   no equivalent of Colab's upload-key-as-file dance; Kaggle owns the secret
#   and the CLI never sees it.
#
# Usage:
#   scripts/train_on_kaggle.sh --smoke [EPOCHS] [BATCH]   # seed-pipeline test
#   scripts/train_on_kaggle.sh [EPOCHS] [BATCH]            # real run, gates enforced
#
# GATING: same as train_on_colab.sh — without --smoke, the readiness gates
# (G1-G5) are enforced locally before anything is pushed to Kaggle.
#
# GPU: only NvidiaTeslaT4, NvidiaTeslaP100, and Tpu1VmV38 are documented in
# the CLI's own SDK (kagglesdk/kernels/types/kernels_api_service.py — "the
# allowed names are in an enum not currently included in kagglesdk"). No
# A100/L4 — an earlier draft of this script wrongly assumed those existed;
# verified false against source before writing this. T4 is the default and
# only supported value here; the memory notes in train_on_colab.sh (batch
# size / host-RAM ceiling) are opf-specific, not Colab-specific, and likely
# apply here too but have NOT been verified on Kaggle's T4 allocation.
#
# What it does:
#   1. enforces the readiness gates locally (unless --smoke)
#   2. publishes/updates a private Kaggle Dataset from data/segmenter_splits/
#   3. generates the kernel script: literal opf_shared.py content + a CONFIG
#      block of literal values (Kaggle's push API has NO environment-variable
#      channel — request.text is the only place per-run config can travel,
#      verified against SaveKernelRequest's fields) + kaggle_train_kernel_body.py
#   4. pushes the kernel (GPU + internet enabled, dataset attached)
#   5. polls kernels_status via the Python API — status is a real
#      KernelWorkerStatus enum (QUEUED/RUNNING/COMPLETE/ERROR), not a string
#      to parse, so failure detection here is exact, unlike Colab's
#      exit-code-marker workaround
#   6. on COMPLETE: downloads /kaggle/working outputs (checkpoint.tar.gz,
#      metrics.json, train.log, eval.log) and extracts the checkpoint
#   7. on ERROR: prints the real failure_message and exits 1

set -euo pipefail

SMOKE=0
if [[ "${1:-}" == "--smoke" ]]; then
  SMOKE=1
  shift
fi

EPOCHS="${1:-1}"
BATCH_SIZE="${2:-1}"
DATA_DIR="data/segmenter_splits"
OUT_DIR="models/decision_segmenter"
KERNEL_DIR="$(mktemp -d)"
DATASET_DIR="$(mktemp -d)"
OPF_PIN_COMMIT="f7f00ca7fb869683eb732c010299d901457f19c3"  # openai/privacy-filter main, 2026-07-15
WANDB_PIN="0.28.0"
GPU="NvidiaTeslaT4"

cleanup() { rm -rf "$KERNEL_DIR" "$DATASET_DIR"; }
trap cleanup EXIT

command -v kaggle >/dev/null || {
  echo "kaggle CLI not found. Install with: uv tool install kaggle" >&2
  exit 1
}

echo "==> resolving Kaggle username from credentials"
# No KAGGLE_USERNAME needed: the API token authenticates and resolves the
# account's username on its own (verified — the KGAT_-prefixed token format
# is self-describing). Requires KAGGLE_KEY (or ~/.kaggle/kaggle.json) to
# already be set in the environment this script runs in.
# uv run --with kaggle: the `kaggle` executable comes from `uv tool install`
# (an isolated tool env), which does NOT make the importable `kaggle` package
# visible to a bare system `python3` — verified live (this failed once with
# ModuleNotFoundError before adding --with kaggle here and below).
KAGGLE_USERNAME="$(uv run --no-project --with kaggle python3 -c "
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi()
api.authenticate()
print(api.config_values.get('username', ''))
")"
[[ -n "$KAGGLE_USERNAME" ]] || {
  echo "Could not resolve Kaggle username — check KAGGLE_KEY / ~/.kaggle/kaggle.json." >&2
  exit 1
}
echo "    authenticated as $KAGGLE_USERNAME"

for f in train.jsonl val.jsonl test.jsonl label_space.json; do
  [[ -f "$DATA_DIR/$f" ]] || { echo "missing $DATA_DIR/$f" >&2; exit 1; }
done

if [[ "$SMOKE" == "1" ]]; then
  JOB_TYPE="smoke-test"
  echo "==> --smoke: readiness gates bypassed (seed-pipeline test, W&B job_type=smoke-test)"
else
  JOB_TYPE="finetune"
  echo "==> enforcing readiness gates (G1-G5) on $DATA_DIR"
  if ! uv run python scripts/prepare_privacy_filter_dataset.py --check-gates --gold-dir "$DATA_DIR"; then
    echo "" >&2
    echo "Readiness gates failed: the corpus is not fit for a real training run." >&2
    echo "To test the pipeline itself on the seed data, re-run with --smoke." >&2
    exit 1
  fi
fi

REPO_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
DATASET_SLUG="causaganha-segmenter-splits"
RUN_ID="$(date +%s)"
KERNEL_SLUG="causaganha-segmenter-train-${RUN_ID}"

echo "==> W&B on Kaggle comes from a kernel Secret (Add-ons -> Secrets in the"
echo "    kernel editor), never from a local env var — the driver installs wandb"
echo "    unconditionally (cheap) and detects a live secret at runtime; whether a"
echo "    secret is attached can't be known before the kernel actually runs."

echo "==> publishing gold splits as Kaggle Dataset $KAGGLE_USERNAME/$DATASET_SLUG"
cp "$DATA_DIR"/{train.jsonl,val.jsonl,test.jsonl,label_space.json} "$DATASET_DIR/"
cat > "$DATASET_DIR/dataset-metadata.json" <<JSON
{
  "id": "$KAGGLE_USERNAME/$DATASET_SLUG",
  "title": "CausaGanha segmenter gold splits",
  "licenses": [{"name": "CC0-1.0"}]
}
JSON
if kaggle datasets metadata "$KAGGLE_USERNAME/$DATASET_SLUG" >/dev/null 2>&1; then
  # --keep-tabular: without it Kaggle auto-converts "tabular-looking" files to
  # CSV on upload, which would corrupt our JSONL.
  kaggle datasets version -p "$DATASET_DIR" -m "sync $REPO_COMMIT" --keep-tabular --dir-mode skip
else
  kaggle datasets create -p "$DATASET_DIR" --keep-tabular --dir-mode skip
fi

echo "==> waiting for dataset processing (create/version returns before it's mounted-ready)"
# Confirmed live: pushing the kernel immediately after create/version raced
# the dataset's own async processing — the kernel started with the dataset
# not yet mounted (FileNotFoundError on label_space.json), even though the
# upload itself had already completed. dataset_status returns a real
# DatabundleVersionStatus enum (READY/FAILED are the terminal states).
uv run --no-project --with kaggle python3 - "$KAGGLE_USERNAME/$DATASET_SLUG" <<'PY'
import sys, time
from kaggle.api.kaggle_api_extended import KaggleApi

dataset = sys.argv[1]
api = KaggleApi()
api.authenticate()

deadline = time.time() + 300
last = None
while time.time() < deadline:
    status = api.dataset_status(dataset)
    if status != last:
        print(f"dataset status: {status}")
        last = status
    if status == "ready":
        sys.exit(0)
    if status == "failed":
        print("Dataset processing failed.", file=sys.stderr)
        sys.exit(1)
    time.sleep(5)
print("Timed out waiting for dataset to become ready.", file=sys.stderr)
sys.exit(1)
PY

echo "==> generating kernel script (opf_shared.py + config + kaggle body)"
{
  cat scripts/opf_shared.py
  echo ""
  echo "# --- CONFIG (generated by train_on_kaggle.sh, do not edit by hand) ---"
  python3 - "$DATASET_SLUG" "$KAGGLE_USERNAME" "$EPOCHS" "$BATCH_SIZE" "$GPU" "$JOB_TYPE" "$OPF_PIN_COMMIT" "$REPO_COMMIT" "$WANDB_PIN" <<'PY'
import sys
slug, owner, epochs, batch, gpu, job_type, opf_commit, repo_commit, wandb_pin = sys.argv[1:]
print(f"DATASET_SLUG = {slug!r}")
print(f"DATASET_OWNER = {owner!r}")
print(f"EPOCHS = {int(epochs)!r}")
print(f"BATCH = {int(batch)!r}")
print(f"GPU = {gpu!r}")
print(f"JOB_TYPE = {job_type!r}")
print(f"OPF_COMMIT = {opf_commit!r}")
print(f"REPO_COMMIT = {repo_commit!r}")
print(f"WANDB_VERSION_PIN = {wandb_pin!r}")
PY
  echo "# --- end CONFIG ---"
  echo ""
  grep -v "KAGGLE_STRIP_THIS_LINE" scripts/kaggle_train_kernel_body.py
} > "$KERNEL_DIR/train.py"

cat > "$KERNEL_DIR/kernel-metadata.json" <<JSON
{
  "id": "$KAGGLE_USERNAME/$KERNEL_SLUG",
  "title": "$KERNEL_SLUG",
  "code_file": "train.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true,
  "dataset_sources": ["$KAGGLE_USERNAME/$DATASET_SLUG"]
}
JSON

echo "==> pushing kernel $KAGGLE_USERNAME/$KERNEL_SLUG (GPU=$GPU)"
kaggle kernels push -p "$KERNEL_DIR" --accelerator "$GPU" --timeout 3600

echo "==> polling for completion (QUEUED -> RUNNING -> COMPLETE/ERROR)"
uv run --no-project --with kaggle python3 - "$KAGGLE_USERNAME/$KERNEL_SLUG" <<'PY'
import sys, time
from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_enums import KernelWorkerStatus

kernel = sys.argv[1]
api = KaggleApi()
api.authenticate()

deadline = time.time() + 3600
last = None
while time.time() < deadline:
    resp = api.kernels_status(kernel)
    if resp.status != last:
        print(f"status: {resp.status.name}")
        last = resp.status
    if resp.status == KernelWorkerStatus.COMPLETE:
        sys.exit(0)
    if resp.status == KernelWorkerStatus.ERROR:
        print(f"Failure message: {resp.failure_message}", file=sys.stderr)
        sys.exit(1)
    time.sleep(15)
print("Timed out waiting for kernel completion.", file=sys.stderr)
sys.exit(1)
PY

echo "==> downloading outputs"
mkdir -p "$OUT_DIR"
kaggle kernels output "$KAGGLE_USERNAME/$KERNEL_SLUG" -p "$OUT_DIR" -o

echo "==> extracting checkpoint"
if [[ -f "$OUT_DIR/checkpoint.tar.gz" ]]; then
  rm -rf "$OUT_DIR/best"
  mkdir -p "$OUT_DIR/best"
  tar -xzf "$OUT_DIR/checkpoint.tar.gz" -C "$OUT_DIR/best"
  echo "==> done: $OUT_DIR/best + $OUT_DIR/metrics.json"
else
  echo "checkpoint.tar.gz not found in output — check $OUT_DIR/train.log" >&2
  exit 1
fi
