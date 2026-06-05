"""Sample judicial decision texts from Internet Archive for segmenter annotation.

Downloads ZIPs from IA items (djen-{tribunal}-{year} format), extracts
texts from JSON files inside, and samples N decisions per tribunal.
Outputs one JSONL per tribunal with raw text + metadata, ready for
annotation.

Usage:
    uv run python scripts/sample_ia_texts.py --tribunal TJRO --n 20 \
        --output-dir data/segmenter_samples
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import sys
import zipfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import structlog


logger = structlog.get_logger()

IA_SEARCH_URL = (
    "https://archive.org/advancedsearch.php?"
    "q=identifier%3A(djen-{tribunal}-*)&fl[]=identifier&rows=50&output=json"
)


TRIBUNAL_TIERS: dict[str, list[str]] = {
    "large_tj": [
        "TJSP",
        "TJRJ",
        "TJMG",
        "TJRS",
        "TJPR",
        "TJSC",
        "TJBA",
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
    "superior": ["STJ", "TST", "STM"],
}


def discover_items(tribunal: str) -> list[str]:
    """Find IA items for a tribunal."""
    url = IA_SEARCH_URL.format(tribunal=tribunal.lower())
    with urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    items = [d["identifier"] for d in data.get("response", {}).get("docs", [])]
    logger.info("discovered_items", tribunal=tribunal, count=len(items))
    return items


def list_zips(item_id: str) -> list[str]:
    """List ZIP files in an IA item."""
    meta_url = f"https://archive.org/metadata/{item_id}/files"
    with urlopen(meta_url, timeout=30) as r:
        files = json.loads(r.read()).get("result", [])
    return [f["name"] for f in files if f["name"].endswith(".zip")]


def download_zip(item_id: str, zip_name: str) -> bytes:
    """Download a single ZIP from IA."""
    url = f"https://archive.org/download/{item_id}/{zip_name}"
    logger.info("downloading_zip", item=item_id, zip=zip_name)
    with urlopen(url, timeout=120) as r:
        return r.read()


def extract_texts_from_zip(zip_bytes: bytes) -> list[dict]:
    """Extract text records from a DJEN ZIP (JSON files inside)."""
    records: list[dict] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            try:
                data = json.loads(zf.read(name))
            except (json.JSONDecodeError, ValueError):
                continue

            items: list = []
            if isinstance(data, dict):
                items = data.get("items", [data])
            elif isinstance(data, list):
                items = data

            for rec in items:
                if not isinstance(rec, dict):
                    continue
                text = (rec.get("texto") or "").strip()
                if len(text) < 200:
                    continue
                records.append(
                    {
                        "text": text,
                        "info": {
                            "id": str(rec.get("id", "")),
                            "tribunal": str(rec.get("tribunal", "")),
                        },
                    }
                )
    return records


def sample_tribunal(
    tribunal: str,
    n: int,
    max_zips: int,
    seed: int,
) -> list[dict]:
    """Sample n texts from a tribunal's IA items."""
    items = discover_items(tribunal)
    if not items:
        logger.warning("no_items_found", tribunal=tribunal)
        return []

    # Reservoir sampling (Algorithm R): retain at most `n` records in memory
    # no matter how many decisions the ZIPs expand to. A single ZIP can hold
    # ~200 MB of JSON, so buffering every extracted decision before truncating
    # to `n` can exhaust a runner. Each unique decision gets an equal chance.
    reservoir: list[dict] = []
    seen_hashes: set[str] = set()
    seen = 0  # unique decisions encountered so far

    rng = random.Random(seed)
    rng.shuffle(items)

    zips_processed = 0
    for item_id in items:
        if zips_processed >= max_zips:
            break
        zip_names = list_zips(item_id)
        trib_zips = [z for z in zip_names if tribunal.upper() in z.upper()]
        if not trib_zips:
            trib_zips = zip_names[:3]
        rng.shuffle(trib_zips)

        for zip_name in trib_zips[:2]:
            if zips_processed >= max_zips:
                break
            try:
                zip_bytes = download_zip(item_id, zip_name)
                texts = extract_texts_from_zip(zip_bytes)
                for rec in texts:
                    h = hashlib.sha256(rec["text"].encode()).hexdigest()
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)
                    rec["info"]["source_item"] = item_id
                    rec["info"]["source_zip"] = zip_name
                    seen += 1
                    if len(reservoir) < n:
                        reservoir.append(rec)
                    else:
                        j = rng.randint(1, seen)
                        if j <= n:
                            reservoir[j - 1] = rec
                zips_processed += 1
                logger.info(
                    "zip_extracted",
                    item=item_id,
                    zip=zip_name,
                    texts=len(texts),
                    sampled=len(reservoir),
                    seen=seen,
                )
            except (URLError, TimeoutError, OSError, zipfile.BadZipFile, ValueError) as e:
                logger.warning("zip_download_failed", item=item_id, zip=zip_name, error=str(e))

    if len(reservoir) < n:
        logger.warning("insufficient_texts", tribunal=tribunal, found=len(reservoir), requested=n)

    rng.shuffle(reservoir)
    return reservoir


def main() -> int:
    parser = argparse.ArgumentParser(description="Sample texts from IA for segmenter annotation")
    parser.add_argument("--tribunal", required=True, help="Tribunal sigla (e.g. TJRO)")
    parser.add_argument("--n", type=int, default=20, help="Number of texts to sample")
    parser.add_argument("--max-zips", type=int, default=10, help="Max ZIPs to download")
    parser.add_argument("--output-dir", default="data/segmenter_samples", help="Output directory")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    tribunal = args.tribunal.upper()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("sampling_start", tribunal=tribunal, n=args.n, seed=args.seed)
    samples = sample_tribunal(tribunal, args.n, args.max_zips, args.seed)

    if not samples:
        logger.error("no_samples", tribunal=tribunal)
        return 1

    out_path = output_dir / f"{tribunal.lower()}.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for rec in samples:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    manifest = {
        "tribunal": tribunal,
        "n_sampled": len(samples),
        "n_requested": args.n,
        "seed": args.seed,
    }
    manifest_path = output_dir / f"{tribunal.lower()}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    logger.info("sampling_done", tribunal=tribunal, n=len(samples), path=str(out_path))
    print(f"Sampled {len(samples)} texts for {tribunal} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
