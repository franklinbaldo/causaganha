#!/usr/bin/env python3
"""Augment segmenter training data with heuristic-labeled texts from IA.

Downloads judicial texts from multiple IA items, applies heuristic
segmentation + regex entity extraction, and merges with cleaned
LLM-labeled data to produce a balanced training set.

Sampling is stratified by tribunal to avoid formatting bias.

Usage:
    uv run python scripts/augment_segmenter_data.py \
        --target 2000 \
        --output-dir models/decision_segmenter
"""

from __future__ import annotations

import argparse
import html
import io
import json
import random
import re
import sys
import uuid
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import structlog

from scripts.prepare_privacy_filter_dataset import LABEL_SPACE_V5, _segment, migrate_spans_v4_to_v5


logger = structlog.get_logger()

NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, "djen.causaganha.org")

IA_SEARCH_URL = (
    "https://archive.org/advancedsearch.php"
    "?q=identifier:djen-*+AND+mediatype:data"
    "&fl[]=identifier&rows={rows}&sort[]=addeddate+desc&output=json"
)

TRIBUNAL_TIERS: dict[str, list[str]] = {
    "large_tj": [
        "TJSP",
        "TJRJ",
        "TJMG",
        "TJRS",
        "TJPR",
        "TJBA",
        "TJSC",
        "TJPE",
        "TJCE",
        "TJDF",
        "TJGO",
        "TJPA",
    ],
    "medium_tj": [
        "TJMA",
        "TJPB",
        "TJRN",
        "TJES",
        "TJMT",
        "TJMS",
        "TJAL",
        "TJPI",
        "TJSE",
        "TJAM",
        "TJRO",
        "TJTO",
        "TJAC",
        "TJAP",
        "TJRR",
    ],
    "trf": ["TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6"],
    "trt": [
        "TRT1",
        "TRT2",
        "TRT3",
        "TRT4",
        "TRT5",
        "TRT6",
        "TRT7",
        "TRT8",
        "TRT9",
        "TRT10",
        "TRT11",
        "TRT12",
        "TRT13",
        "TRT14",
        "TRT15",
        "TRT17",
        "TRT18",
        "TRT19",
        "TRT20",
        "TRT21",
        "TRT22",
        "TRT23",
        "TRT24",
    ],
    "superior": ["STJ", "TST", "STM"],
}

ALL_TRIBUNALS: set[str] = set()
for _tier in TRIBUNAL_TIERS.values():
    ALL_TRIBUNALS.update(_tier)

TIER_WEIGHTS = {
    "large_tj": 0.40,
    "medium_tj": 0.25,
    "trf": 0.10,
    "trt": 0.15,
    "superior": 0.10,
}

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = _HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_texto(raw: str) -> str:
    """Clean raw texto: strip HTML if present, normalize whitespace."""
    if "<" in raw and ">" in raw:
        return _strip_html(raw)
    return re.sub(r"[ \t]+", " ", raw).strip()


def discover_items(n_items: int = 20) -> list[str]:
    """Find djen-* items on IA (tribunal-year format: djen-tjro-2025)."""
    url = IA_SEARCH_URL.format(rows=n_items)
    with urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    items = [d["identifier"] for d in data.get("response", {}).get("docs", [])]
    logger.info("discovered_items", count=len(items))
    return items


def list_zips(item_id: str) -> list[str]:
    """List ZIP files in an IA item."""
    meta_url = f"https://archive.org/metadata/{item_id}/files"
    try:
        with urlopen(meta_url, timeout=30) as r:
            files = json.loads(r.read()).get("result", [])
        return [f["name"] for f in files if f["name"].endswith(".zip")]
    except (URLError, OSError) as e:
        logger.warning("list_zips_failed", item=item_id, error=str(e))
        return []


def _parse_tribunal_from_zip(zip_name: str) -> str:
    """Extract tribunal sigla from ZIP filename like djen-2025-01-27-TJSP.zip."""
    stem = zip_name.replace(".zip", "")
    parts = stem.split("-")
    if len(parts) >= 4:
        return "-".join(parts[4:]).upper() if len(parts) > 4 else parts[-1].upper()
    return ""


def _build_zip_index(
    items: list[str],
) -> dict[str, list[tuple[str, str]]]:
    """Map tribunal sigla → [(item_id, zip_name), ...] across all items."""
    index: dict[str, list[tuple[str, str]]] = defaultdict(list)

    def _fetch(item: str) -> list[tuple[str, str, str]]:
        zips = list_zips(item)
        results = []
        for z in zips:
            trib = _parse_tribunal_from_zip(z)
            if trib:
                results.append((trib, item, z))
        return results

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch, item): item for item in items}
        for fut in as_completed(futures):
            for trib, item, z in fut.result():
                index[trib].append((item, z))

    logger.info(
        "zip_index_built",
        tribunals=len(index),
        total_zips=sum(len(v) for v in index.values()),
    )
    return dict(index)


def _sample_zips(
    index: dict[str, list[tuple[str, str]]],
    target_texts: int,
    texts_per_zip: int = 50,
) -> list[tuple[str, str, str]]:
    """Sample ZIPs across tribunals proportionally by tier.

    Returns [(tribunal, item_id, zip_name), ...].
    """
    total_zips_needed = max(target_texts // texts_per_zip, 20)
    sampled: list[tuple[str, str, str]] = []

    for tier_name, weight in TIER_WEIGHTS.items():
        tier_tribunals = TRIBUNAL_TIERS[tier_name]
        available = [t for t in tier_tribunals if t in index]
        if not available:
            continue

        tier_budget = max(int(total_zips_needed * weight), 1)
        per_tribunal = max(tier_budget // len(available), 1)

        for trib in available:
            pool = index[trib]
            n = min(per_tribunal, len(pool))
            chosen = random.sample(pool, n)
            for item, z in chosen:
                sampled.append((trib, item, z))

    random.shuffle(sampled)
    logger.info("zips_sampled", count=len(sampled))
    return sampled


def _extract_texts_from_zip(
    item_id: str,
    zip_name: str,
    tribunal: str,
    max_per_zip: int = 100,
) -> list[dict]:
    """Download a ZIP and extract cleaned texts."""
    url = f"https://archive.org/download/{item_id}/{zip_name}"
    try:
        with urlopen(url, timeout=120) as r:
            content = r.read()
    except (URLError, OSError) as e:
        logger.warning("zip_download_failed", zip=zip_name, error=str(e))
        return []

    rows: list[dict] = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for name in zf.namelist():
                if not name.endswith(".json"):
                    continue
                try:
                    data = json.loads(zf.read(name))
                except json.JSONDecodeError:
                    continue

                items = []
                if isinstance(data, dict):
                    items = data.get("items", [data])
                elif isinstance(data, list):
                    items = data

                for rec in items:
                    if not isinstance(rec, dict):
                        continue
                    raw_texto = (rec.get("texto") or "").strip()
                    if len(raw_texto) < 200:
                        continue

                    texto = _clean_texto(raw_texto)
                    if len(texto) < 200:
                        continue

                    uid = str(uuid.uuid5(NAMESPACE_DJEN, texto[:500]))
                    rows.append(
                        {
                            "id": uid,
                            "texto": texto,
                            "tribunal": tribunal,
                        }
                    )
                    if len(rows) >= max_per_zip:
                        break
                if len(rows) >= max_per_zip:
                    break
    except zipfile.BadZipFile:
        logger.warning("bad_zip", zip=zip_name)
        return []

    return rows


def _label_text(texto: str) -> dict[str, list[list[int]]] | None:
    """Apply heuristic segmentation. Returns None if no dispositivo found."""
    return _segment(texto)


def _clean_llm_records(parquet_path: Path) -> list[dict]:
    """Load LLM-labeled parquet, apply P0 cleanup, return OPF records."""
    import ibis

    t = ibis.read_parquet(parquet_path)
    df = t.filter(t.texto.notnull()).execute()
    logger.info("llm_records_loaded", count=len(df))

    seen_textos: set[str] = set()
    records: list[dict] = []
    dropped = Counter({"duplicate": 0, "no_spans": 0, "no_sections": 0, "overlap": 0})

    for _, row in df.iterrows():
        texto = row["texto"]
        spans_raw = row.get("spans_json", "")
        if not spans_raw:
            dropped["no_spans"] += 1
            continue

        text_key = texto[:200]
        if text_key in seen_textos:
            dropped["duplicate"] += 1
            continue
        seen_textos.add(text_key)

        spans = json.loads(spans_raw)
        spans_clean: dict[str, list[list[int]]] = {}
        has_section = False

        for k, v in spans.items():
            if not v or not isinstance(v, list):
                continue
            clean_pairs = []
            for pair in v:
                s, e = int(pair[0]), int(pair[1])
                if 0 <= s < e <= len(texto):
                    clean_pairs.append([s, e])
            if clean_pairs:
                spans_clean[k] = clean_pairs
                if k.startswith("sec_"):
                    has_section = True

        if not has_section:
            dropped["no_sections"] += 1
            continue

        records.append({"text": texto, "spans": migrate_spans_v4_to_v5(spans_clean)})

    logger.info("llm_cleanup", kept=len(records), dropped=dict(dropped))
    return records


def write_jsonl(records: list[dict], path: Path) -> None:
    """Write records to JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    logger.info("jsonl_written", path=str(path), count=len(records))


def main() -> int:
    parser = argparse.ArgumentParser(description="Augment segmenter training data")
    parser.add_argument(
        "--target",
        type=int,
        default=2000,
        help="Target number of heuristic-labeled records",
    )
    parser.add_argument(
        "--max-per-tribunal",
        type=int,
        default=150,
        help="Max records per tribunal (prevents bias)",
    )
    parser.add_argument(
        "--llm-parquet",
        type=Path,
        default=Path("data/benchmark/segmenter_training.parquet"),
        help="Path to LLM-labeled parquet (cleaned and merged)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("models/decision_segmenter"),
        help="Output directory for JSONL files",
    )
    parser.add_argument(
        "--n-items",
        type=int,
        default=15,
        help="Number of IA items to scan for ZIPs (tribunal-year items)",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    # --- Phase 1: Discover and sample ZIPs across tribunals ---
    logger.info("phase1_discover", n_items=args.n_items, target=args.target)
    items = discover_items(args.n_items)
    if not items:
        logger.error("no_items_found")
        return 1

    index = _build_zip_index(items)
    sampled_zips = _sample_zips(index, args.target)

    # --- Phase 2: Download and extract texts ---
    logger.info("phase2_download", zips=len(sampled_zips))
    all_texts: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {
            pool.submit(
                _extract_texts_from_zip,
                item,
                z,
                trib,
            ): (trib, item, z)
            for trib, item, z in sampled_zips
        }
        for i, fut in enumerate(as_completed(futures), 1):
            texts = fut.result()
            all_texts.extend(texts)
            if i % 10 == 0 or i == len(sampled_zips):
                logger.info(
                    "download_progress",
                    done=i,
                    total=len(sampled_zips),
                    texts=len(all_texts),
                )

    # Deduplicate by text prefix
    seen: set[str] = set()
    unique_texts: list[dict] = []
    for t in all_texts:
        key = t["texto"][:200]
        if key not in seen:
            seen.add(key)
            unique_texts.append(t)

    logger.info("texts_extracted", total=len(all_texts), unique=len(unique_texts))

    # --- Phase 3: Apply heuristic labels ---
    logger.info("phase3_label")
    labeled: list[dict] = []
    tribunal_counts: Counter[str] = Counter()
    skipped_no_disp = 0

    random.shuffle(unique_texts)

    for t in unique_texts:
        trib = t["tribunal"]
        if tribunal_counts[trib] >= args.max_per_tribunal:
            continue

        spans = _label_text(t["texto"])
        if spans is None:
            skipped_no_disp += 1
            continue

        labeled.append({"text": t["texto"], "spans": spans})
        tribunal_counts[trib] += 1

        if len(labeled) >= args.target:
            break

    logger.info(
        "heuristic_labeling_done",
        labeled=len(labeled),
        skipped_no_dispositivo=skipped_no_disp,
        tribunals=len(tribunal_counts),
    )

    # Log per-tribunal distribution
    for trib, count in sorted(tribunal_counts.items(), key=lambda x: -x[1]):
        logger.info("tribunal_distribution", tribunal=trib, count=count)

    # --- Phase 4: Clean and merge LLM data ---
    llm_records: list[dict] = []
    if args.llm_parquet.exists():
        llm_records = _clean_llm_records(args.llm_parquet)
        logger.info("llm_records_cleaned", count=len(llm_records))

    all_records = llm_records + labeled
    random.shuffle(all_records)

    logger.info(
        "merged_dataset",
        total=len(all_records),
        llm=len(llm_records),
        heuristic=len(labeled),
    )

    # --- Phase 5: Split and write ---
    n = len(all_records)
    train_end = int(n * 0.8)
    val_end = train_end + int(n * 0.1)

    train_records = all_records[:train_end]
    val_records = all_records[train_end:val_end]
    test_records = all_records[val_end:]

    logger.info("splits", train=len(train_records), val=len(val_records), test=len(test_records))

    output_dir = args.output_dir
    write_jsonl(train_records, output_dir / "train.jsonl")
    write_jsonl(val_records, output_dir / "val.jsonl")
    write_jsonl(test_records, output_dir / "test.jsonl")

    label_space_path = output_dir / "label_space.json"
    label_space_path.write_text(
        json.dumps(LABEL_SPACE_V5, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("label_space_written", path=str(label_space_path))

    # Coverage report
    label_coverage: Counter[str] = Counter()
    for rec in all_records:
        for label in rec["spans"]:
            label_coverage[label] += 1

    print(f"\n{'=' * 60}")
    print("AUGMENTED DATASET SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total records: {len(all_records)} (LLM: {len(llm_records)}, Heuristic: {len(labeled)})")
    print(f"Tribunals: {len(tribunal_counts)}")
    print(f"Train/Val/Test: {len(train_records)}/{len(val_records)}/{len(test_records)}")
    print("\nLabel coverage (records containing each label):")
    for label, count in sorted(label_coverage.items(), key=lambda x: -x[1]):
        pct = count / len(all_records) * 100
        print(f"  {label:<22} {count:>5} ({pct:.1f}%)")
    print("\nTribunal distribution:")
    for trib, count in sorted(tribunal_counts.items(), key=lambda x: -x[1])[:20]:
        print(f"  {trib:<8} {count:>5}")
    if len(tribunal_counts) > 20:
        print(f"  ... and {len(tribunal_counts) - 20} more")
    print(f"{'=' * 60}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
