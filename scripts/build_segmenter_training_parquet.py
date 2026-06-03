#!/usr/bin/env python3
"""Build a training-ready Parquet for the decision segmenter from LLM labels.

Reads LLM-annotated batch JSONs (section boundaries + entity text spans),
resolves them to character offsets via string matching, and outputs a Parquet
with columns: text_uuid, texto, spans_json, court, label_source.

Usage:
    uv run python scripts/build_segmenter_training_parquet.py \
        --labels-dir /tmp/seg_labels \
        --benchmark data/benchmark/gold_benchmark.parquet \
        --output data/segmenter_training.parquet
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import structlog


logger = structlog.get_logger()

SECTION_ORDER = [
    "sec_cabecalho",
    "sec_relatorio",
    "sec_fundamentacao",
    "sec_dispositivo",
    "sec_assinatura",
]

ENTITY_LABELS = [
    "processo_cnj",
    "oab",
    "nome_advogado",
    "nome_juiz",
    "parte_autor",
    "parte_reu",
    "parte_terceiro",
    "cpf_cnpj",
    "classe_processual",
    "data",
    "valor_monetario",
    "id_lei",
    "id_precedente",
    "citacao_precedente",
    "serventuario",
    "elem_nao_textual",
]


def _find_substring(text: str, needle: str) -> int | None:
    """Find needle in text, trying exact match then case-insensitive."""
    idx = text.find(needle)
    if idx >= 0:
        return idx
    idx = text.lower().find(needle.lower())
    if idx >= 0:
        return idx
    needle_clean = re.sub(r"\s+", " ", needle).strip()
    text_clean = re.sub(r"\s+", " ", text)
    idx = text_clean.find(needle_clean)
    if idx >= 0:
        orig_pos = 0
        clean_pos = 0
        while clean_pos < idx and orig_pos < len(text):
            if text[orig_pos] in (" ", "\t", "\n", "\r"):
                if clean_pos < len(text_clean) and text_clean[clean_pos] == " ":
                    clean_pos += 1
                orig_pos += 1
                while orig_pos < len(text) and text[orig_pos] in (" ", "\t", "\n", "\r"):
                    orig_pos += 1
            else:
                clean_pos += 1
                orig_pos += 1
        return orig_pos
    return None


def resolve_sections(text: str, sections: dict) -> dict[str, list[tuple[int, int]]]:
    """Convert section start/end text markers to character offset spans."""
    boundaries: list[tuple[int, str]] = []

    for sec_name in SECTION_ORDER:
        sec_info = sections.get(sec_name)
        if not sec_info:
            continue
        start_text = sec_info.get("start_text", "")
        if not start_text:
            continue
        pos = _find_substring(text, start_text[:40])
        if pos is not None:
            boundaries.append((pos, sec_name))

    boundaries.sort(key=lambda x: x[0])

    result: dict[str, list[tuple[int, int]]] = {}
    for i, (start, name) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        result.setdefault(name, []).append((start, end))

    return result


def resolve_entities(text: str, entities: dict) -> dict[str, list[tuple[int, int]]]:
    """Convert entity text spans to character offset spans."""
    result: dict[str, list[tuple[int, int]]] = {}

    for label_name in ENTITY_LABELS:
        spans = entities.get(label_name, [])
        if not spans:
            continue
        if isinstance(spans, str):
            spans = [spans]

        found_positions: list[tuple[int, int]] = []
        for span_text in spans:
            if not span_text or not isinstance(span_text, str):
                continue
            pos = _find_substring(text, span_text)
            if pos is not None:
                found_positions.append((pos, pos + len(span_text)))
            else:
                span_short = span_text[:60]
                pos = _find_substring(text, span_short)
                if pos is not None:
                    found_positions.append((pos, pos + len(span_short)))

        if found_positions:
            result[label_name] = found_positions

    return result


def process_batch_file(batch_path: Path, texts_by_uuid: dict[str, str]) -> list[dict]:
    """Process a single LLM label batch file."""
    try:
        labels = json.loads(batch_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("batch_read_error", path=str(batch_path), error=str(e))
        return []

    records = []
    for item in labels:
        text_uuid = item.get("text_uuid", "")
        texto = texts_by_uuid.get(text_uuid, "")
        if not texto:
            continue

        sections_raw = item.get("sections", {})
        entities_raw = item.get("entities", {})

        spans: dict[str, list[tuple[int, int]]] = {}
        spans.update(resolve_sections(texto, sections_raw))
        spans.update(resolve_entities(texto, entities_raw))

        if not spans:
            logger.warning("no_spans_resolved", text_uuid=text_uuid)
            continue

        spans_serializable = {k: [[s, e] for s, e in v] for k, v in spans.items()}
        records.append(
            {
                "text_uuid": text_uuid,
                "texto": texto,
                "spans_json": json.dumps(spans_serializable, ensure_ascii=False),
                "label_source": "llm",
            }
        )

    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Build segmenter training parquet")
    parser.add_argument(
        "--labels-dir",
        default="/tmp/seg_labels",
        help="Directory with LLM label batch JSONs",
    )
    parser.add_argument(
        "--benchmark",
        default="data/benchmark/gold_benchmark.parquet",
        help="Benchmark parquet with texto column",
    )
    parser.add_argument(
        "--output",
        default="data/benchmark/segmenter_training.parquet",
        help="Output parquet path",
    )
    args = parser.parse_args()

    import ibis  # noqa: PLC0415

    bench = ibis.read_parquet(args.benchmark)
    df = bench.select("text_uuid", "texto", "court").execute()
    texts_by_uuid = {row["text_uuid"]: row["texto"] for _, row in df.iterrows()}
    court_by_uuid = {row["text_uuid"]: row["court"] for _, row in df.iterrows()}
    logger.info("loaded_benchmark", texts=len(texts_by_uuid))

    labels_dir = Path(args.labels_dir)
    batch_files = sorted(labels_dir.glob("batch_*.json"))
    logger.info("found_batch_files", count=len(batch_files))

    all_records: list[dict] = []
    for bf in batch_files:
        records = process_batch_file(bf, texts_by_uuid)
        all_records.extend(records)
        logger.info("processed_batch", file=bf.name, records=len(records))

    for rec in all_records:
        rec["court"] = court_by_uuid.get(rec["text_uuid"], "")

    if not all_records:
        logger.error("no_records_produced")
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    table = pa.table(
        {
            "text_uuid": [r["text_uuid"] for r in all_records],
            "texto": [r["texto"] for r in all_records],
            "spans_json": [r["spans_json"] for r in all_records],
            "court": [r["court"] for r in all_records],
            "label_source": [r["label_source"] for r in all_records],
        }
    )
    pq.write_table(table, output_path)
    logger.info("training_parquet_written", path=str(output_path), records=len(all_records))

    label_counts: dict[str, int] = {}
    for r in all_records:
        spans = json.loads(r["spans_json"])
        for k in spans:
            label_counts[k] = label_counts.get(k, 0) + len(spans[k])

    print(f"\nTraining data summary: {len(all_records)} texts")
    print("Label span counts:")
    for k, v in sorted(label_counts.items(), key=lambda x: -x[1]):
        print(f"  {k:<25} {v}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
