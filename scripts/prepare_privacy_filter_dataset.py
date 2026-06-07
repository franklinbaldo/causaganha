#!/usr/bin/env python3
"""Prepare anchor-span dataset for CausaGanha decision segmenter (OPF v7).

Two modes:
  1. PROMOTE (default): Read gold splits from git (data/segmenter_splits/),
     validate, write manifest, publish to output dir (Drive/IA cache).
  2. BOOTSTRAP: Generate initial heuristic labels from a parquet of judicial
     texts. Output needs LLM verification before becoming gold.

Ontology v7 — two anchor schemes:
  Single-anchor (6): short cue, region extends to next anchor/EOD.
  Start/end pairs (8x2=16): discrete regions with _inicio/_fim markers.
  Total: O + 22 = 23 entries in span_class_names.

Output: OPF-format JSONL — one record per line:
  {"text": str, "label": [{"category": str, "start": int, "end": int}],
   "info": {"id": str}}

Usage:
    # Promote gold splits (normal flow):
    uv run python scripts/prepare_privacy_filter_dataset.py

    # Bootstrap from parquet (initial data generation):
    uv run python scripts/prepare_privacy_filter_dataset.py \
        --bootstrap --parquet data/test_parquets/textos.parquet
"""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import structlog


logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Label space v7 — CausaGanha anchor-span ontology
#
# Two anchor schemes:
#   Single-anchor (6): short cue, region extends to next anchor or EOD.
#   Start/end pairs (8x2=16): _inicio/_fim bracket discrete regions.
#
# ref_normativa is a single-anchor category but is handled by regex
# pre-pass at inference time. It is kept in SINGLE_ANCHOR_CATEGORIES
# for region reconstruction but excluded from the OPF training label
# space (SPAN_CLASS_NAMES_V7).
#
# Training label space: O + 5 trained single + 16 paired = 22 entries.
# Full ontology: O + 6 single + 16 paired = 23 entries.
# ---------------------------------------------------------------------------

# -- Single-anchor categories (tiling regions) --
SINGLE_ANCHOR_CATEGORIES: list[str] = [
    "dispositivo_abertura",
    "resultado",
    "ref_processual",
    "valor_condenacao",
    "ref_normativa",
    "fundamentacao_legal",
]

# -- Start/end pair categories (discrete regions) --
_PAIRED_REGION_BASES: list[str] = [
    "cabecalho",
    "ementa",
    "relatorio",
    "capitulo_merito",
    "preliminar",
    "honorarios",
    "custas",
    "encerramento",
]

PAIRED_CATEGORIES: list[str] = []
for _base in _PAIRED_REGION_BASES:
    PAIRED_CATEGORIES.extend([f"{_base}_inicio", f"{_base}_fim"])

_TRAINED_SINGLE = [c for c in SINGLE_ANCHOR_CATEGORIES if c != "ref_normativa"]

SPAN_CLASS_NAMES_V7: list[str] = [
    "O",
    *_TRAINED_SINGLE,
    *PAIRED_CATEGORIES,
]

LABEL_SPACE_V7 = {
    "category_version": "segmenter_v7",
    "span_class_names": SPAN_CLASS_NAMES_V7,
}

# v6 kept for migration / backwards compat
SPAN_CLASS_NAMES_V6: list[str] = [
    "O",
    "dispositivo_abertura",
    "resultado",
    "ref_processual",
    "valor_condenacao",
    "ref_normativa",
]

LABEL_SPACE_V6 = {
    "category_version": "causaganha_v6",
    "span_class_names": SPAN_CLASS_NAMES_V6,
}

# Current-version aliases — all new code should use these
SPAN_CLASS_NAMES = SPAN_CLASS_NAMES_V7
LABEL_SPACE = LABEL_SPACE_V7

# Backwards compat for importers expecting older names
LABEL_SPACE_V5 = LABEL_SPACE_V6
SPAN_CLASS_NAMES_V5 = SPAN_CLASS_NAMES_V6

# Gold splits live in git (source of truth)
GOLD_DIR = Path("data/segmenter_splits")

# ---------------------------------------------------------------------------
# Anchor-span patterns (used in bootstrap mode only)
# ---------------------------------------------------------------------------

_DISPOSITIVO_ABERTURA_RE = re.compile(
    r"(?:Ante\s+(?:todo\s+o|ao|o)\s+exposto"
    r"|Posto\s+isso"
    r"|Isso\s+posto"
    r"|Isto\s+posto"
    r"|Diante\s+do\s+exposto"
    r"|Pelo\s+exposto"
    r"|Em\s+face\s+do\s+exposto"
    r"|Por\s+tais\s+fundamentos"
    r"|Nestes\s+termos"
    r"|Em\s+conclus[ãa]o"
    r"|Pelo\s+que\s+exposto"
    r"|Em\s+vista\s+do\s+exposto"
    r"|Por\s+(?:todo\s+o\s+)?exposto"
    r"|Por\s+essas\s+raz[oõ]es"
    r"|Em\s+raz[aã]o\s+do\s+exposto"
    r"|Ex\s+positis)",
    re.IGNORECASE,
)

_RESULTADO_RE = re.compile(
    r"(?:julgo\s+(?:parcialmente\s+)?(?:procedente|improcedente)"
    r"|julgo\s+extinto"
    r"|extingo\s+o\s+(?:feito|processo)(?:\s+sem\s+resolu[çc][ãa]o\s+de\s+m[eé]rito)?"
    r"|nego\s+provimento"
    r"|dou\s+provimento"
    r"|dou\s+parcial\s+provimento"
    r"|nego\s+seguimento"
    r"|conhe[çc]o\s+(?:e\s+)?nego\s+provimento"
    r"|conhe[çc]o\s+(?:e\s+)?dou\s+provimento"
    r"|homologo\s+(?:o\s+)?(?:acordo|desist[eê]ncia|transa[çc][ãa]o)"
    r"|acolho\s+(?:o\s+)?(?:pedido|requerimento)"
    r"|indefiro\s+(?:o\s+)?(?:pedido|requerimento)"
    r"|defiro\s+(?:o\s+)?(?:pedido|requerimento)"
    r"|rejeito\s+(?:os?\s+)?(?:embargos|pedido)"
    r"|acolho\s+(?:os?\s+)?embargos"
    r"|declaro\s+(?:a\s+)?(?:prescri[çc][ãa]o|decad[eê]ncia|nulidade)"
    r"|condeno\s+(?:o\s+r[eé]u|a\s+parte\s+r[eé])"
    r"|absolvo\s+(?:o\s+r[eé]u|a\s+parte\s+r[eé])"
    r"|confirmo\s+a\s+senten[çc]a"
    r"|reformo\s+a\s+senten[çc]a"
    r"|anulo\s+a\s+senten[çc]a)",
    re.IGNORECASE,
)

_REF_PROCESSUAL_RE = re.compile(
    r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}"
    r"|fls?\.\s*\d+(?:/\d+)?(?:\s*(?:v|verso))?",
    re.IGNORECASE,
)

_VALOR_CONDENACAO_RE = re.compile(
    r"R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}"
    r"|R\$\s*\d+,\d{2}",
)


# ---------------------------------------------------------------------------
# Segmentation — anchor spans only (bootstrap mode)
# ---------------------------------------------------------------------------


def _collect_spans(
    pattern: re.Pattern[str],
    text: str,
    category: str,
    *,
    start: int = 0,
    end: int | None = None,
) -> list[dict]:
    if end is None:
        end = len(text)
    spans = []
    for m in pattern.finditer(text, start, end):
        s, e = m.start(), m.end()
        surface = text[s:e]
        trimmed = surface.strip()
        if trimmed and trimmed != surface:
            s += surface.index(trimmed)
            e = s + len(trimmed)
        if s < e:
            spans.append({"category": category, "start": s, "end": e})
    return spans


def _remove_overlaps(spans: list[dict]) -> list[dict]:
    spans_sorted = sorted(spans, key=lambda s: (s["start"], -s["end"]))
    result = []
    last_end = -1
    for sp in spans_sorted:
        if sp["start"] >= last_end:
            result.append(sp)
            last_end = sp["end"]
    return result


def segment(text: str) -> list[dict] | None:
    """Return OPF-format span list for a judicial decision text.

    Returns None if no dispositivo opening cue is found (required anchor).
    Keeps only the LAST dispositivo match (the operative one) per v7 rules.
    """
    all_disp = _collect_spans(_DISPOSITIVO_ABERTURA_RE, text, "dispositivo_abertura")
    if not all_disp:
        return None

    operative_disp = max(all_disp, key=lambda s: s["start"])
    disp_start = operative_disp["start"]
    spans: list[dict] = [operative_disp]

    spans.extend(_collect_spans(_RESULTADO_RE, text, "resultado", start=disp_start))
    spans.extend(_collect_spans(_REF_PROCESSUAL_RE, text, "ref_processual"))
    spans.extend(
        _collect_spans(
            _VALOR_CONDENACAO_RE,
            text,
            "valor_condenacao",
            start=disp_start,
        )
    )
    return _remove_overlaps(spans)


def _segment(text: str) -> dict[str, list[list[int]]] | None:
    """Compat wrapper: returns old dict-of-lists format for legacy callers."""
    spans = segment(text)
    if spans is None:
        return None
    result: dict[str, list[list[int]]] = {}
    for sp in spans:
        result.setdefault(sp["category"], []).append([sp["start"], sp["end"]])
    return result


_V6_CATEGORIES = frozenset(SPAN_CLASS_NAMES_V6)
_V7_CATEGORIES = frozenset(SPAN_CLASS_NAMES_V7)


def migrate_spans_v4_to_v5(
    spans: dict[str, list[list[int]]],
) -> dict[str, list[list[int]]]:
    """Keep only categories that exist in the v6 ontology, reject unknown ones."""
    kept = {k: v for k, v in spans.items() if k in _V6_CATEGORIES and k != "O"}
    unknown = set(spans) - _V6_CATEGORIES
    if unknown and not kept:
        msg = (
            f"All categories are legacy/unknown: {sorted(unknown)}. "
            f"Valid v6 categories: {sorted(_V6_CATEGORIES - {'O'})}"
        )
        raise ValueError(msg)
    return kept


def migrate_spans_v6_to_v7(
    spans: dict[str, list[list[int]]],
) -> dict[str, list[list[int]]]:
    """Keep only categories that exist in the v7 ontology, reject unknown ones."""
    kept = {k: v for k, v in spans.items() if k in _V7_CATEGORIES and k != "O"}
    unknown = set(spans) - _V7_CATEGORIES
    if unknown and not kept:
        msg = (
            f"All categories are legacy/unknown: {sorted(unknown)}. "
            f"Valid v7 categories: {sorted(_V7_CATEGORIES - {'O'})}"
        )
        raise ValueError(msg)
    return kept


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------


def _validate_split(jsonl_path: Path, label_space_path: Path) -> bool:
    cmd = [
        sys.executable,
        str(Path(__file__).parent / "opf_annotate.py"),
        "validate",
        str(jsonl_path),
        "--label-space",
        str(label_space_path),
    ]
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Promote mode: read gold from git, validate, publish
# ---------------------------------------------------------------------------


def _get_source_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except FileNotFoundError:
        return "unknown"


def promote_gold(gold_dir: Path, output_dir: Path) -> int:
    """Read gold splits from git, validate, write manifest, publish."""
    required = ["train.jsonl", "val.jsonl", "test.jsonl", "label_space.json"]
    missing = [f for f in required if not (gold_dir / f).exists()]
    if missing:
        logger.error("missing_gold_files", gold_dir=str(gold_dir), missing=missing)
        print(
            f"Error: gold dir {gold_dir} is missing {missing}.\n"
            f"Run with --bootstrap first to generate initial data, "
            f"then verify with subagents before committing.",
            file=sys.stderr,
        )
        return 1

    ls_path = gold_dir / "label_space.json"
    ls = json.loads(ls_path.read_text(encoding="utf-8"))
    names = ls.get("span_class_names", [])
    if not names or names[0] != "O":
        logger.error("invalid_label_space", first_entry=names[0] if names else "empty")
        return 1

    logger.info("validating_gold_splits")
    all_valid = True
    for split in ("train", "val", "test"):
        jsonl = gold_dir / f"{split}.jsonl"
        if not _validate_split(jsonl, ls_path):
            logger.error("validation_failed", split=split)
            all_valid = False
        else:
            logger.info("validation_passed", split=split)
    if not all_valid:
        return 1

    # Count records and categories
    split_counts = {}
    cat_counts: dict[str, int] = {}
    for split in ("train", "val", "test"):
        jsonl = gold_dir / f"{split}.jsonl"
        count = 0
        with jsonl.open(encoding="utf-8") as f:
            for raw in f:
                stripped = raw.strip()
                if not stripped:
                    continue
                rec = json.loads(stripped)
                count += 1
                for sp in rec.get("label", []):
                    cat = sp.get("category", "")
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
        split_counts[split] = count

    # Read existing manifest or create new
    existing_manifest_path = gold_dir / "manifest.json"
    if existing_manifest_path.exists():
        manifest = json.loads(existing_manifest_path.read_text(encoding="utf-8"))
        manifest["counts"] = split_counts
        manifest["per_class"] = cat_counts
        manifest["source_commit"] = _get_source_commit()
    else:
        manifest = {
            "category_version": ls.get("category_version", "causaganha_v6"),
            "seed": 42,
            "source_commit": _get_source_commit(),
            "counts": split_counts,
            "per_class": cat_counts,
            "test_verified_by": "same_as_train_labeler",
        }

    # Publish to output dir
    output_dir.mkdir(parents=True, exist_ok=True)
    for f in [*required, "manifest.json"]:
        src = gold_dir / f
        dst = output_dir / f
        if src.exists():
            dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    manifest_out = output_dir / "manifest.json"
    manifest_out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(
        "gold_promoted",
        gold_dir=str(gold_dir),
        output_dir=str(output_dir),
        counts=split_counts,
        test_verified_by=manifest.get("test_verified_by", "unknown"),
    )
    return 0


# ---------------------------------------------------------------------------
# Stratified splitting
# ---------------------------------------------------------------------------


def _pop_from_duplicate_category(records: list[dict]) -> dict:
    """Pop a record from a category that has multiple training examples."""
    cat_indices: dict[str, list[int]] = {}
    for i, rec in enumerate(records):
        cat = _dominant_category(rec)
        cat_indices.setdefault(cat, []).append(i)
    for cat in sorted(cat_indices, key=lambda c: -len(cat_indices[c])):
        if len(cat_indices[cat]) > 1:
            return records.pop(cat_indices[cat][-1])
    return records.pop()


def _dominant_category(rec: dict) -> str:
    """Return the most frequent category in a record's labels (for stratification)."""
    cats: dict[str, int] = {}
    for sp in rec.get("label", []):
        c = sp.get("category", "O")
        cats[c] = cats.get(c, 0) + 1
    return max(cats, key=cats.get) if cats else "O"


def _stratified_split(
    records: list[dict],
    *,
    seed: int = 42,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
) -> dict[str, list[dict]]:
    """Split records into train/val/test preserving category distribution."""
    rng = random.Random(seed)

    buckets: dict[str, list[dict]] = {}
    for rec in records:
        cat = _dominant_category(rec)
        buckets.setdefault(cat, []).append(rec)

    train, val, test = [], [], []
    for cat in sorted(buckets):
        items = buckets[cat]
        rng.shuffle(items)
        n = len(items)
        n_train = max(1, int(n * train_ratio))
        n_val = max(1, int(n * val_ratio)) if n > 2 else 0
        train.extend(items[:n_train])
        val.extend(items[n_train : n_train + n_val])
        test.extend(items[n_train + n_val :])

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)

    if not val and train:
        val.append(_pop_from_duplicate_category(train))
    if not test and train:
        test.append(_pop_from_duplicate_category(train))

    logger.info(
        "stratified_split",
        train=len(train),
        val=len(val),
        test=len(test),
        strata=len(buckets),
    )
    return {"train": train, "val": val, "test": test}


# ---------------------------------------------------------------------------
# Bootstrap mode: generate heuristic labels from parquet
# ---------------------------------------------------------------------------


def bootstrap_from_parquet(parquet_path: Path, output_dir: Path, seed: int) -> int:
    """Generate initial heuristic labels from parquet. Needs LLM verification."""
    import ibis  # noqa: PLC0415

    if not parquet_path.exists():
        logger.error("parquet_not_found", path=str(parquet_path))
        return 1

    logger.info("loading_parquet", path=str(parquet_path))
    t = ibis.read_parquet(parquet_path)
    df = t.filter(t.texto.notnull()).execute()
    logger.info("loaded_texts", count=len(df))

    records: list[dict] = []
    skipped = 0
    for _, row in df.iterrows():
        spans = segment(row["texto"])
        if spans is None:
            skipped += 1
            continue
        records.append(
            {
                "text": row["texto"],
                "label": spans,
                "info": {"id": row.get("id", "")},
            }
        )

    logger.info("segmentation_done", records=len(records), skipped=skipped)

    # Deduplicate by text hash to prevent train/test leakage
    import hashlib  # noqa: PLC0415

    seen: set[str] = set()
    unique_records: list[dict] = []
    for rec in records:
        h = hashlib.sha256(rec["text"].encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            unique_records.append(rec)
    if len(unique_records) < len(records):
        logger.info(
            "deduplicated",
            before=len(records),
            after=len(unique_records),
            removed=len(records) - len(unique_records),
        )
    records = unique_records

    if len(records) < 10:
        logger.error("insufficient_data", count=len(records))
        return 1

    cat_counts: dict[str, int] = {}
    for rec in records:
        for sp in rec["label"]:
            cat_counts[sp["category"]] = cat_counts.get(sp["category"], 0) + 1
    for cat, count in sorted(cat_counts.items()):
        logger.info("category_count", category=cat, spans=count)

    splits = _stratified_split(records, seed=seed)

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in splits.items():
        path = output_dir / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for rec in data:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        logger.info("split_written", split=name, path=str(path), count=len(data))

    ls_path = output_dir / "label_space.json"
    ls_path.write_text(json.dumps(LABEL_SPACE_V7, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest = {
        "category_version": LABEL_SPACE_V7["category_version"],
        "seed": seed,
        "source_commit": _get_source_commit(),
        "counts": {name: len(data) for name, data in splits.items()},
        "per_class": cat_counts,
        "test_verified_by": "same_as_train_labeler",
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(
        "bootstrap_done",
        output_dir=str(output_dir),
        train=len(splits["train"]),
        val=len(splits["val"]),
        test=len(splits["test"]),
    )
    print(
        f"\nBootstrap data written to {output_dir}/.\n"
        f"  test_verified_by: same_as_train_labeler (NEEDS VERIFICATION)\n"
        f"  Next: verify with subagent ensemble, then commit to {GOLD_DIR}/",
        file=sys.stderr,
    )
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare CausaGanha anchor-span dataset (OPF v7)")
    parser.add_argument(
        "--gold-dir",
        default=str(GOLD_DIR),
        help="Directory with gold splits in git (default: data/segmenter_splits)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/segmenter_v7",
        help="Output directory for runtime artifacts (Drive/IA cache)",
    )
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="Bootstrap mode: generate heuristic labels from parquet",
    )
    parser.add_argument(
        "--parquet",
        default="data/test_parquets/textos.parquet",
        help="Parquet path (bootstrap mode only)",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.bootstrap:
        return bootstrap_from_parquet(
            Path(args.parquet),
            Path(args.output_dir),
            args.seed,
        )
    return promote_gold(Path(args.gold_dir), Path(args.output_dir))


if __name__ == "__main__":
    sys.exit(main())
