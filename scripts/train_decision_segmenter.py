#!/usr/bin/env python3
r"""Train a 22-class decision segmenter using the opf CLI (openai/privacy-filter).

Converts labeled data (LLM-labeled parquet or heuristic-labeled texts) into the
JSONL format expected by `opf train`, writes label_space.json, then shells out
to the opf CLI for training and evaluation.

Usage:
    # From LLM-labeled parquet (recommended):
    uv run python scripts/train_decision_segmenter.py \
        --labeled-parquet data/benchmark/segmenter_training.parquet \
        --output-dir models/decision_segmenter

    # From IA-downloaded texts with heuristic labeling:
    uv run python scripts/train_decision_segmenter.py \
        --download-from djen-tjro-2025 --n-zips 50 \
        --output-dir models/decision_segmenter
"""

from __future__ import annotations

import argparse
import io
import json
import random
import subprocess
import sys
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import structlog

from scripts.prepare_privacy_filter_dataset import (
    LABEL_SPACE,
    _segment,
)


logger = structlog.get_logger()

NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, "djen.causaganha.org")


def download_textos(ia_item: str, n_zips: int | None, output_path: Path) -> Path:
    """Download ZIPs from IA and extract texts into a parquet."""
    import pyarrow as pa  # noqa: PLC0415
    import pyarrow.parquet as pq  # noqa: PLC0415

    logger.info("listing_zips", item=ia_item)
    meta_url = f"https://archive.org/metadata/{ia_item}/files"
    with urlopen(meta_url) as r:
        ia_files = json.loads(r.read()).get("result", [])
    zips = sorted(
        f["name"] for f in ia_files if f["name"].startswith("djen-") and f["name"].endswith(".zip")
    )
    if n_zips:
        zips = zips[:n_zips]
    logger.info("downloading_zips", count=len(zips))

    def _extract(zip_name: str) -> list[dict]:
        url = f"https://archive.org/download/{ia_item}/{zip_name}"
        try:
            with urlopen(url, timeout=120) as r:
                content = r.read()
            rows = []
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for name in zf.namelist():
                    if not name.endswith(".json"):
                        continue
                    try:
                        data = json.loads(zf.read(name))
                    except json.JSONDecodeError:
                        continue
                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict):
                        items = data.get("items", [data])
                    else:
                        items = []
                    for rec in items:
                        if not isinstance(rec, dict):
                            continue
                        texto = (rec.get("texto") or "").strip()
                        if len(texto) >= 200:
                            uid = str(uuid.uuid5(NAMESPACE_DJEN, texto))
                            rows.append({"id": uid, "texto": texto})
            return rows
        except (URLError, zipfile.BadZipFile, OSError, ValueError) as e:
            logger.warning("zip_error", zip=zip_name, error=str(e))
            return []

    all_rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_extract, z): z for z in zips}
        for i, fut in enumerate(as_completed(futures), 1):
            all_rows.extend(fut.result())
            if i % 10 == 0 or i == len(zips):
                logger.info("progress", done=i, total=len(zips), texts=len(all_rows))

    seen: set[str] = set()
    unique_rows = []
    for row in all_rows:
        if row["id"] not in seen:
            seen.add(row["id"])
            unique_rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "id": [r["id"] for r in unique_rows],
            "texto": [r["texto"] for r in unique_rows],
        }
    )
    pq.write_table(table, output_path)
    logger.info("textos_saved", path=str(output_path), count=len(unique_rows))
    return output_path


def build_records(parquet_path: Path) -> list[dict]:
    """Segment texts with heuristic regex and return OPF-format records."""
    import ibis  # noqa: PLC0415

    t = ibis.read_parquet(parquet_path)
    df = t.filter(t.texto.notnull()).execute()
    logger.info("loaded_texts", count=len(df))

    records: list[dict] = []
    skipped = 0
    for _, row in df.iterrows():
        spans = _segment(row["texto"])
        if spans is None:
            skipped += 1
            continue
        records.append({"text": row["texto"], "spans": spans})

    logger.info("segmentation_done", records=len(records), skipped=skipped)
    return records


def build_records_from_labeled(parquet_path: Path) -> list[dict]:
    """Load pre-labeled records (LLM or human annotated) with spans_json column."""
    import ibis  # noqa: PLC0415

    t = ibis.read_parquet(parquet_path)
    df = t.filter(t.texto.notnull()).execute()
    logger.info("loaded_labeled_texts", count=len(df))

    records: list[dict] = []
    for _, row in df.iterrows():
        spans_raw = row.get("spans_json", "")
        if not spans_raw:
            continue
        spans = json.loads(spans_raw)
        spans_clean = {
            k: [list(pair) for pair in v] for k, v in spans.items() if v and isinstance(v, list)
        }
        records.append({"text": row["texto"], "spans": spans_clean})

    logger.info("labeled_records_loaded", records=len(records))
    return records


def write_jsonl(records: list[dict], path: Path) -> None:
    """Write records to JSONL in OPF's expected format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    logger.info("jsonl_written", path=str(path), count=len(records))


def run_opf_train(
    train_jsonl: Path,
    val_jsonl: Path,
    label_space_json: Path,
    output_dir: Path,
    *,
    epochs: int = 3,
    batch_size: int = 8,
) -> int:
    """Shell out to `opf train`."""
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
        "--epochs",
        str(epochs),
        "--batch-size",
        str(batch_size),
    ]
    logger.info("opf_train_start", cmd=" ".join(cmd))
    result = subprocess.run(cmd, check=False)
    logger.info("opf_train_done", returncode=result.returncode)
    return result.returncode


def run_opf_eval(
    test_jsonl: Path,
    model_dir: Path,
    label_space_json: Path,
    metrics_output: Path,
) -> dict | None:
    """Shell out to `opf eval` and parse metrics."""
    cmd = [
        sys.executable,
        "-m",
        "opf",
        "eval",
        str(test_jsonl),
        "--model-dir",
        str(model_dir),
        "--label-space-json",
        str(label_space_json),
    ]
    logger.info("opf_eval_start", cmd=" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    logger.info("opf_eval_done", returncode=result.returncode)

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        return None

    metrics_output.parent.mkdir(parents=True, exist_ok=True)

    try:
        for raw_line in result.stdout.strip().splitlines():
            stripped = raw_line.strip()
            if stripped.startswith("{"):
                metrics = json.loads(stripped)
                metrics_output.write_text(
                    json.dumps(metrics, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                return metrics
    except (json.JSONDecodeError, ValueError):
        pass

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Train decision segmenter via opf")
    parser.add_argument(
        "--parquet",
        default="data/test_parquets/textos.parquet",
        help="Path to textos.parquet (for heuristic labeling)",
    )
    parser.add_argument(
        "--download-from",
        metavar="IA_ITEM",
        help="Download ZIPs from this IA item (e.g. djen-tjro-2025)",
    )
    parser.add_argument("--n-zips", type=int, default=50, help="Number of ZIPs to download")
    parser.add_argument(
        "--output-dir",
        default="models/decision_segmenter",
        help="Output directory for model and metrics",
    )
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument(
        "--labeled-parquet",
        metavar="PATH",
        help="Pre-labeled parquet with spans_json column (LLM/human labels). "
        "Skips heuristic segmentation.",
    )
    args = parser.parse_args()

    # Build records
    if args.labeled_parquet:
        labeled_path = Path(args.labeled_parquet)
        if not labeled_path.exists():
            logger.error("labeled_parquet_not_found", path=str(labeled_path))
            return 1
        records = build_records_from_labeled(labeled_path)
    else:
        parquet_path = Path(args.parquet)
        if args.download_from:
            parquet_path = download_textos(args.download_from, args.n_zips, parquet_path)
        elif not parquet_path.exists():
            logger.error("parquet_not_found", path=str(parquet_path))
            msg = f"Error: {parquet_path} not found. Use --download-from to fetch data."
            print(msg, file=sys.stderr)
            return 1
        records = build_records(parquet_path)

    if len(records) < 10:
        logger.error("insufficient_data", count=len(records))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Split into train/val/test (80/10/10)
    random.seed(42)
    random.shuffle(records)
    n = len(records)
    train_end = int(n * 0.8)
    val_end = train_end + int(n * 0.1)

    train_records = records[:train_end]
    val_records = records[train_end:val_end]
    test_records = records[val_end:]

    logger.info("splits", train=len(train_records), val=len(val_records), test=len(test_records))

    # Write JSONL files
    train_jsonl = output_dir / "train.jsonl"
    val_jsonl = output_dir / "val.jsonl"
    test_jsonl = output_dir / "test.jsonl"

    write_jsonl(train_records, train_jsonl)
    write_jsonl(val_records, val_jsonl)
    write_jsonl(test_records, test_jsonl)

    # Write label_space.json
    label_space_path = output_dir / "label_space.json"
    label_space_path.write_text(
        json.dumps(LABEL_SPACE, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("label_space_written", path=str(label_space_path))

    # Train with opf
    checkpoint_dir = output_dir / "best"
    rc = run_opf_train(
        train_jsonl,
        val_jsonl,
        label_space_path,
        checkpoint_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
    )
    if rc != 0:
        logger.error("opf_train_failed", returncode=rc)
        return rc

    # Evaluate on test set
    metrics_path = output_dir / "test_metrics.json"
    metrics = run_opf_eval(test_jsonl, checkpoint_dir, label_space_path, metrics_path)

    if not metrics:
        logger.error("opf_eval_failed")
        return 1

    macro = metrics.get("macro avg", {})
    print(f"\nMacro F1: {macro.get('f1-score', 0):.3f}")
    disp = metrics.get("sec_dispositivo", {})
    print(f"sec_dispositivo F1: {disp.get('f1-score', 0):.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
