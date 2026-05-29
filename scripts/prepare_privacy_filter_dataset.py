#!/usr/bin/env python3
"""Prepare span-extraction dataset for training a judicial decision segmenter.

Reads textos.parquet from data/test_parquets, applies heuristic segmentation to
label each decision's text with three structural spans:

    relatorio     — case history / summary (beginning of decision)
    fundamentacao — legal reasoning (middle)
    dispositivo   — operative ruling (end, after ante-o-exposto markers)

Outputs JSONL files (train / validation / test) compatible with HuggingFace
token-classification fine-tuning, plus label_space.json.

Usage:
    uv run python scripts/prepare_privacy_filter_dataset.py
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

import ibis
import structlog


logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Heuristic segmentation markers
# ---------------------------------------------------------------------------

_DISPOSITIVO_RE = re.compile(
    r"(?:ante\s+o\s+exposto|posto\s+isso|isso\s+posto|"
    r"diante\s+do\s+exposto|pelo\s+exposto|em\s+face\s+do\s+exposto|"
    r"por\s+tais\s+fundamentos|nestes\s+termos|em\s+conclus[ãa]o|"
    r"pelo\s+que\s+exposto|em\s+vista\s+do\s+exposto)",
    re.IGNORECASE,
)

_FUNDAMENTACAO_RE = re.compile(
    r"(?:fundament[ao](?:ção)?|m[eé]rito|an[aá]lise\s+do\s+pedido|"
    r"da\s+an[aá]lise|do\s+m[eé]rito|"
    r"fundamenta[çc][aã]o\s+(?:jur[ií]dica|do\s+ju[ií]zo))",
    re.IGNORECASE,
)


def _segment(text: str) -> dict[str, list[list[int]]] | None:
    """Return character-level span dict for the three decision sections.

    Returns None if the dispositivo section cannot be located.
    Spans: {label: [[start, end], ...]}
    """
    dispositivo_match = _DISPOSITIVO_RE.search(text)
    if not dispositivo_match:
        return None

    dispositivo_start = dispositivo_match.start()

    # Search for fundamentação only in the pre-dispositivo portion
    pre_disp = text[:dispositivo_start]
    fund_match = _FUNDAMENTACAO_RE.search(pre_disp)

    if fund_match:
        fund_start = fund_match.start()
        relatorio_end = fund_start
    else:
        # No explicit marker: treat first half as relatório
        relatorio_end = len(pre_disp) // 2
        fund_start = relatorio_end

    spans: dict[str, list[list[int]]] = {}
    if relatorio_end > 0:
        spans["relatorio"] = [[0, relatorio_end]]
    if dispositivo_start > fund_start:
        spans["fundamentacao"] = [[fund_start, dispositivo_start]]
    spans["dispositivo"] = [[dispositivo_start, len(text)]]

    return spans


def main() -> int:
    logger.info("starting_dataset_preparation")

    textos_file = Path("data/test_parquets/textos.parquet")
    output_dir = Path("data/privacy_filter")
    output_dir.mkdir(parents=True, exist_ok=True)

    if not textos_file.exists():
        logger.error("textos_parquet_missing", path=str(textos_file))
        return 1

    logger.info("loading_textos_parquet")
    t = ibis.read_parquet(textos_file)
    df = t.filter(t.texto.notnull()).execute()
    logger.info("textos_loaded", count=len(df))

    records: list[dict] = []
    skipped = 0

    for _, row in df.iterrows():
        text: str = row["texto"]
        spans = _segment(text)
        if spans is None:
            skipped += 1
            continue
        records.append({"text": text, "spans": spans})

    logger.info("segmentation_complete", total=len(records), skipped=skipped)

    if not records:
        logger.error("no_records_to_write")
        return 1

    random.seed(42)
    random.shuffle(records)

    n = len(records)
    train_end = int(n * 0.8)
    val_end = train_end + int(n * 0.1)

    splits = {
        "train": records[:train_end],
        "validation": records[train_end:val_end],
        "test": records[val_end:],
    }
    logger.info("splitting", **{k: len(v) for k, v in splits.items()})

    for name, data in splits.items():
        path = output_dir / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for r in data:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        logger.info("saved", file=str(path), count=len(data))

    label_space = {
        "category_version": "causaganha_v2",
        "span_class_names": ["relatorio", "fundamentacao", "dispositivo"],
    }
    label_space_path = output_dir / "label_space.json"
    label_space_path.write_text(
        json.dumps(label_space, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("label_space_saved", file=str(label_space_path))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
