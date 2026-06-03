#!/usr/bin/env python3
r"""Train a 22-class decision segmenter by fine-tuning openai/privacy-filter.

Purpose:  Produce a token-classification model that segments Brazilian judicial
          decisions into structural sections and named entities.
Problem:  The base openai/privacy-filter has a 33-class PII head; we replace it
          with a 22-class judicial head and fine-tune on silver-labeled data.
Strategy: Heuristic segmentation produces silver labels (regex for sections,
          patterns for entities); the model generalises beyond the heuristics.
Status:   research/training — run via GHA workflow or locally.

Usage:
    uv run python scripts/train_decision_segmenter.py \
        --parquet data/test_parquets/textos.parquet \
        --output-dir models/decision_segmenter \
        --epochs 3 --batch-size 16

    # Download textos from IA first:
    uv run python scripts/train_decision_segmenter.py \
        --download-from djen-tjro-2025 --n-zips 50 \
        --output-dir models/decision_segmenter
"""

from __future__ import annotations

import argparse
import io
import json
import random
import sys
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import numpy as np
import structlog

from scripts.prepare_privacy_filter_dataset import (
    LABEL_SPACE,
    SPAN_CLASS_NAMES,
    _segment,
)


logger = structlog.get_logger()

NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, "djen.causaganha.org")

ID2LABEL = dict(enumerate(SPAN_CLASS_NAMES))
LABEL2ID = {name: i for i, name in ID2LABEL.items()}
NUM_LABELS = len(SPAN_CLASS_NAMES)

_SECTION_LABELS = frozenset(
    {
        "sec_cabecalho",
        "sec_relatorio",
        "sec_fundamentacao",
        "sec_dispositivo",
        "sec_assinatura",
        "elem_nao_textual",
    }
)

_ENTITY_PRIORITY = [
    "classe_processual",
    "data",
    "valor_monetario",
    "citacao_precedente",
    "id_lei",
    "id_precedente",
    "parte_autor",
    "parte_reu",
    "parte_terceiro",
    "nome_advogado",
    "nome_juiz",
    "serventuario",
    "oab",
    "processo_cnj",
    "cpf_cnpj",
]


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
    """Segment texts and return labeled records."""
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


def tokenize_and_label(example: dict, tokenizer: object, max_length: int = 512) -> dict:
    """Convert text + char spans to token-level labels."""
    text = example["text"]
    spans = example["spans"]
    char_labels = np.zeros(len(text), dtype=np.int32)

    for label_name, span_list in spans.items():
        if label_name not in _SECTION_LABELS:
            continue
        lid = LABEL2ID.get(label_name, 0)
        for start, end in span_list:
            char_labels[start : min(end, len(text))] = lid

    remaining = {k: v for k, v in spans.items() if k not in _SECTION_LABELS}
    ordered = [la for la in _ENTITY_PRIORITY if la in remaining]
    ordered += [la for la in remaining if la not in _ENTITY_PRIORITY]
    for label_name in ordered:
        lid = LABEL2ID.get(label_name, 0)
        for start, end in remaining[label_name]:
            char_labels[start : min(end, len(text))] = lid

    enc = tokenizer(text, truncation=True, max_length=max_length, return_offsets_mapping=True)
    offsets = enc.pop("offset_mapping")
    token_labels = []
    for start, end in offsets:
        if start == end:
            token_labels.append(-100)
        else:
            token_labels.append(int(char_labels[start]))
    enc["labels"] = token_labels
    return enc


def train(
    records: list[dict],
    output_dir: Path,
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    max_length: int = 512,
    *,
    fp16: bool = False,
) -> dict:
    """Fine-tune the model and return test metrics."""
    from datasets import Dataset  # noqa: PLC0415
    from sklearn.metrics import classification_report  # noqa: PLC0415
    from transformers import (  # noqa: PLC0415
        AutoModelForTokenClassification,
        AutoTokenizer,
        DataCollatorForTokenClassification,
        Trainer,
        TrainingArguments,
    )

    model_name = "openai/privacy-filter"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    random.seed(42)
    random.shuffle(records)
    n = len(records)
    train_end = int(n * 0.8)
    val_end = train_end + int(n * 0.1)

    raw_train = Dataset.from_list(records[:train_end])
    raw_val = Dataset.from_list(records[train_end:val_end])
    raw_test = Dataset.from_list(records[val_end:])

    logger.info("splits", train=len(raw_train), val=len(raw_val), test=len(raw_test))

    def _tokenize(example: dict) -> dict:
        return tokenize_and_label(example, tokenizer, max_length)

    train_ds = raw_train.map(_tokenize, remove_columns=["text", "spans"])
    val_ds = raw_val.map(_tokenize, remove_columns=["text", "spans"])
    test_ds = raw_test.map(_tokenize, remove_columns=["text", "spans"])

    model = AutoModelForTokenClassification.from_pretrained(
        model_name,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
        trust_remote_code=True,
    )

    def compute_metrics(p: tuple) -> dict:
        logits, labels = p
        preds = np.argmax(logits, axis=-1)
        y_true, y_pred = [], []
        for pred_row, label_row in zip(preds, labels, strict=True):
            for p_id, l_id in zip(pred_row, label_row, strict=True):
                if l_id == -100:
                    continue
                y_true.append(ID2LABEL[l_id])
                y_pred.append(ID2LABEL[p_id])
        report = classification_report(
            y_true,
            y_pred,
            labels=[la for la in SPAN_CLASS_NAMES if la != "O"],
            output_dict=True,
            zero_division=0,
        )
        macro = report.get("macro avg", {})
        result = {
            "macro_f1": macro.get("f1-score", 0),
            "macro_precision": macro.get("precision", 0),
            "macro_recall": macro.get("recall", 0),
        }
        for lbl in [
            "sec_dispositivo",
            "sec_fundamentacao",
            "sec_relatorio",
            "processo_cnj",
            "id_lei",
            "id_precedente",
            "data",
        ]:
            result[f"f1_{lbl}"] = report.get(lbl, {}).get("f1-score", 0)
        return result

    total_steps = (len(train_ds) // batch_size) * epochs
    warmup_steps = max(50, total_steps // 10)

    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size * 2,
        learning_rate=learning_rate,
        warmup_steps=warmup_steps,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        fp16=fp16,
        logging_steps=50,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=DataCollatorForTokenClassification(tokenizer),
        compute_metrics=compute_metrics,
    )

    logger.info("training_start", epochs=epochs, batch_size=batch_size)
    trainer.train()

    # Evaluate on test set
    logger.info("evaluating_test_set")
    preds_out = trainer.predict(test_ds)
    preds = np.argmax(preds_out.predictions, axis=-1)
    labels = preds_out.label_ids

    y_true, y_pred = [], []
    for pred_row, label_row in zip(preds, labels, strict=True):
        for p_id, l_id in zip(pred_row, label_row, strict=True):
            if l_id == -100:
                continue
            y_true.append(ID2LABEL[l_id])
            y_pred.append(ID2LABEL[p_id])

    report_text = classification_report(
        y_true,
        y_pred,
        labels=[la for la in SPAN_CLASS_NAMES if la != "O"],
        zero_division=0,
    )
    report_dict = classification_report(
        y_true,
        y_pred,
        labels=[la for la in SPAN_CLASS_NAMES if la != "O"],
        output_dict=True,
        zero_division=0,
    )

    print("\n" + "=" * 70)
    print("TEST SET CLASSIFICATION REPORT")
    print("=" * 70)
    print(report_text)

    # Save model
    best_dir = output_dir / "best"
    trainer.save_model(str(best_dir))
    tokenizer.save_pretrained(str(best_dir))
    label_space_path = best_dir / "label_space.json"
    label_space_path.write_text(
        json.dumps(LABEL_SPACE, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("model_saved", path=str(best_dir))

    # Save metrics
    metrics_path = output_dir / "test_metrics.json"
    metrics_path.write_text(json.dumps(report_dict, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("metrics_saved", path=str(metrics_path))

    return report_dict


def main() -> int:
    parser = argparse.ArgumentParser(description="Train decision segmenter")
    parser.add_argument(
        "--parquet",
        default="data/test_parquets/textos.parquet",
        help="Path to textos.parquet",
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
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--fp16", action="store_true", help="Use mixed precision (GPU only)")
    args = parser.parse_args()

    parquet_path = Path(args.parquet)

    if args.download_from:
        parquet_path = download_textos(args.download_from, args.n_zips, parquet_path)
    elif not parquet_path.exists():
        logger.error("parquet_not_found", path=str(parquet_path))
        msg = f"Error: {parquet_path} not found. Use --download-from to fetch data."
        print(msg, file=sys.stderr)
        return 1

    records = build_records(parquet_path)
    if len(records) < 100:
        logger.error("insufficient_data", count=len(records))
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = train(
        records,
        output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        max_length=args.max_length,
        fp16=args.fp16,
    )

    macro = report.get("macro avg", {})
    print(f"\nMacro F1: {macro.get('f1-score', 0):.3f}")
    print(f"sec_dispositivo F1: {report.get('sec_dispositivo', {}).get('f1-score', 0):.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
