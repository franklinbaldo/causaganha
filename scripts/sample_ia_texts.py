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
import json
import random
import re
import sys
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


def get_zip_json_links(item_id: str, zip_name: str) -> list[str]:
    """Fetch HTML list of JSON files inside the ZIP virtual directory."""
    url = f"https://archive.org/download/{item_id}/{zip_name}/"
    logger.info("fetching_zip_virtual_dir", url=url)
    try:
        with urlopen(url, timeout=30) as r:
            html = r.read().decode("utf-8")
        links = re.findall(r'href=["\']([^"\']+\.json)["\']', html)
        absolute_links = []
        for link in links:
            if link.startswith("//"):
                absolute_links.append(f"https:{link}")
            elif link.startswith("/"):
                absolute_links.append(f"https://archive.org{link}")
            elif not link.startswith("http"):
                absolute_links.append(f"https://archive.org/download/{item_id}/{zip_name}/{link}")
            else:
                absolute_links.append(link)
        return absolute_links
    except Exception as e:
        logger.warning("failed_to_fetch_zip_virtual_dir", url=url, error=str(e))
        return []


def extract_texts_from_json_url(url: str) -> list[dict]:
    """Fetch a single JSON file from virtual ZIP path and extract text records."""
    try:
        with urlopen(url, timeout=30) as r:
            data = json.loads(r.read())
    except Exception as e:
        logger.warning("failed_to_fetch_json_url", url=url, error=str(e))
        return []

    items = []
    if isinstance(data, dict):
        items = data.get("items", [data])
    elif isinstance(data, list):
        items = data

    records = []
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

    all_texts: list[dict] = []
    seen_hashes: set[str] = set()

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
                json_urls = get_zip_json_links(item_id, zip_name)
                if not json_urls:
                    continue

                rng.shuffle(json_urls)
                texts = []
                for json_url in json_urls[:10]:
                    fetched = extract_texts_from_json_url(json_url)
                    texts.extend(fetched)
                    if len(all_texts) + len(texts) >= n + 10:
                        break

                for rec in texts:
                    h = hashlib.sha256(rec["text"].encode()).hexdigest()
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        rec["info"]["source_item"] = item_id
                        rec["info"]["source_zip"] = zip_name
                        all_texts.append(rec)
                zips_processed += 1
                logger.info(
                    "zip_streamed",
                    item=item_id,
                    zip=zip_name,
                    jsons=len(json_urls),
                    extracted=len(texts),
                    total=len(all_texts),
                )
            except (URLError, TimeoutError, OSError, ValueError) as e:
                logger.warning("zip_streaming_failed", item=item_id, zip=zip_name, error=str(e))

    if len(all_texts) < n:
        logger.warning("insufficient_texts", tribunal=tribunal, found=len(all_texts), requested=n)
        return all_texts

    rng.shuffle(all_texts)
    return all_texts[:n]


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
