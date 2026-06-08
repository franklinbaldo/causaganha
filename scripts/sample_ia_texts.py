"""Sample judicial decision texts from Internet Archive for segmenter annotation.

Fetches individual JSON files directly from inside IA ZIP items (no full
ZIP download). Each inner JSON contains ~1000 intimações. Records are
filtered by document type and scored by rare-class cue density to
prioritize docs that exercise the v7 ontology's underrepresented categories.

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
import time
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

ALL_TRIBUNALS = [t for tier in TRIBUNAL_TIERS.values() for t in tier]

SENTENCA_TYPES = {"Sentença", "Decisão"}
ACORDAO_TYPES = {"Decisão", "Acórdão"}

COLLEGIATE_ORGAN = re.compile(
    r"Turma\b|C[âa]mara\b|Se[çc][ãa]o(?!\s+Judici)\b|Plen[áa]rio",
    re.IGNORECASE,
)

RARE_CLASS_CUES: dict[str, re.Pattern[str]] = {
    "preliminar": re.compile(r"\bPRELIMINAR|DAS PRELIMINARES", re.IGNORECASE),
    "honorarios": re.compile(r"\bhonor[áa]rios\b", re.IGNORECASE),
    "custas": re.compile(r"\bcustas\b", re.IGNORECASE),
    "voto": re.compile(r"\bVOTO\b|É o voto|É como voto"),
    "acordao_decisorio": re.compile(r"\bACORDAM\b|unanimidade|por maioria", re.IGNORECASE),
    "dispositivo": re.compile(
        r"Ante o exposto|Pelo exposto|Posto isso|Diante do exposto",
        re.IGNORECASE,
    ),
    "ementa": re.compile(r"\bEMENTA:"),
    "relatorio": re.compile(r"\bRELAT[ÓO]RIO:|\bTrata-se de\b", re.IGNORECASE),
    "encerramento": re.compile(r"Publique-se|P\.R\.I\.", re.IGNORECASE),
    "cabecalho": re.compile(r"PODER JUDICI[ÁA]RIO|TRIBUNAL DE JUSTI[ÇC]A", re.IGNORECASE),
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


def list_inner_jsons(item_id: str, zip_name: str) -> list[str]:
    """List JSON files inside a ZIP via IA's directory listing."""
    url = f"https://archive.org/download/{item_id}/{zip_name}/"
    with urlopen(url, timeout=30) as r:
        html = r.read().decode("utf-8", errors="replace")
    matches = re.findall(r'href="([^"]*\.json)"', html)
    return [m.split("/")[-1] for m in matches]


def fetch_json_records(item_id: str, zip_name: str, json_name: str) -> list[dict]:
    """Fetch a single JSON file from inside a ZIP — no ZIP download."""
    url = f"https://archive.org/download/{item_id}/{zip_name}/{json_name}"
    logger.info("fetching_json", item=item_id, zip=zip_name, json=json_name)
    with urlopen(url, timeout=120) as r:
        data = json.loads(r.read())
    records = []
    items = []
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
                    "tipoDocumento": (rec.get("tipoDocumento") or "").strip(),
                    "nomeOrgao": (rec.get("nomeOrgao") or "").strip(),
                    "nomeClasse": (rec.get("nomeClasse") or "").strip(),
                },
            }
        )
    return records


def score_record(texto: str) -> tuple[dict[str, bool], int]:
    """Score a text by rare-class cue presence."""
    hits = {name: bool(pat.search(texto)) for name, pat in RARE_CLASS_CUES.items()}
    return hits, sum(hits.values())


def filter_and_score_record(rec: dict, mode: str) -> dict | None:
    """Apply structured gate + regex scoring to a record."""
    text = rec["text"]
    tipo = rec["info"].get("tipoDocumento", "")
    orgao = rec["info"].get("nomeOrgao", "")

    cue_hits, cue_score = score_record(text)

    allowed = ACORDAO_TYPES if mode == "acordao" else SENTENCA_TYPES
    if tipo and tipo not in allowed:
        return None
    if not tipo and not cue_hits.get("dispositivo"):
        return None

    is_collegiate = bool(COLLEGIATE_ORGAN.search(orgao))
    if mode == "acordao":
        has_acordam = bool(re.search(r"\bACORDAM\b", text[:2000]))
        if not (is_collegiate or has_acordam):
            return None
    elif is_collegiate:
        return None

    rec["cue_hits"] = cue_hits
    rec["cue_score"] = cue_score
    return rec


def sample_tribunal(
    tribunal: str,
    n: int,
    max_zips: int,
    seed: int,
    mode: str,
) -> list[dict]:
    """Sample n texts from a tribunal's IA items, prioritizing rare class cues."""
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
        try:
            zip_names = list_zips(item_id)
        except (URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as e:
            logger.warning("list_zips_failed", item=item_id, error=str(e))
            continue

        trib_zips = [z for z in zip_names if tribunal.upper() in z.upper()]
        if not trib_zips:
            trib_zips = zip_names[:3]
        rng.shuffle(trib_zips)

        for zip_name in trib_zips[:2]:
            if zips_processed >= max_zips:
                break
            try:
                inner_jsons = list_inner_jsons(item_id, zip_name)
                if not inner_jsons:
                    continue
                rng.shuffle(inner_jsons)
                
                # Try up to 5 inner JSON files from the same ZIP until we get matches
                for json_name in inner_jsons[:5]:
                    try:
                        texts = fetch_json_records(item_id, zip_name, json_name)
                        zip_texts = []
                        for rec in texts:
                            filtered_rec = filter_and_score_record(rec, mode)
                            if filtered_rec is None:
                                continue
                            h = hashlib.sha256(filtered_rec["text"].encode()).hexdigest()
                            if h not in seen_hashes:
                                seen_hashes.add(h)
                                filtered_rec["info"]["source_item"] = item_id
                                filtered_rec["info"]["source_zip"] = zip_name
                                filtered_rec["info"]["source_json"] = json_name
                                filtered_rec["info"]["sha256"] = h
                                zip_texts.append(filtered_rec)
                        
                        if zip_texts:
                            all_texts.extend(zip_texts)
                            zips_processed += 1
                            logger.info(
                                "zip_extracted",
                                item=item_id,
                                zip=zip_name,
                                json=json_name,
                                texts=len(texts),
                                matched=len(zip_texts),
                                total=len(all_texts),
                            )
                            break
                        else:
                            logger.info("json_no_matches", item=item_id, zip=zip_name, json=json_name)
                    except (URLError, TimeoutError, OSError, ValueError) as e:
                        logger.warning("json_fetch_failed", item=item_id, zip=zip_name, json=json_name, error=str(e))
            except (URLError, TimeoutError, OSError, ValueError) as e:
                logger.warning("zip_fetch_failed", item=item_id, zip=zip_name, error=str(e))

    if not all_texts:
        return []

    # Sort descending by cue score to prioritize rare-class cues
    all_texts.sort(key=lambda r: r["cue_score"], reverse=True)

    if len(all_texts) < n:
        logger.warning("insufficient_texts", tribunal=tribunal, found=len(all_texts), requested=n)
        return all_texts

    return all_texts[:n]


def main() -> int:
    parser = argparse.ArgumentParser(description="Sample texts from IA for segmenter annotation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tribunal", help="Tribunal sigla (e.g. TJRO)")
    group.add_argument("--all", action="store_true", help="All tribunals")
    parser.add_argument(
        "--mode",
        choices=["sentenca", "acordao"],
        default="sentenca",
        help="sentenca: Sentença/Decisão types; acordao: collegiate bodies",
    )
    parser.add_argument("--n", type=int, default=20, help="Number of texts to sample")
    parser.add_argument("--max-zips", type=int, default=10, help="Max ZIPs to download")
    parser.add_argument("--output-dir", default="data/segmenter_samples", help="Output directory")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tribunals = ALL_TRIBUNALS if args.all else [args.tribunal.upper()]

    summary: dict[str, dict] = {}
    for tribunal in tribunals:
        logger.info("sampling_start", tribunal=tribunal, n=args.n, seed=args.seed, mode=args.mode)
        samples = sample_tribunal(tribunal, args.n, args.max_zips, args.seed, args.mode)

        if not samples:
            logger.error("no_samples", tribunal=tribunal)
            summary[tribunal] = {"status": "empty", "n": 0}
            continue

        suffix = f"_{args.mode}" if args.mode != "sentenca" else ""
        out_path = output_dir / f"{tribunal.lower()}{suffix}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for rec in samples:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        summary[tribunal] = {
            "status": "ok",
            "n": len(samples),
            "top_score": samples[0]["cue_score"],
            "source": samples[0]["info"]["source_item"],
            "path": str(out_path),
        }

        per_trib_manifest = output_dir / f"{tribunal.lower()}{suffix}_manifest.json"
        per_trib_manifest.write_text(
            json.dumps(
                {
                    "tribunal": tribunal,
                    "n_sampled": len(samples),
                    "n_requested": args.n,
                    "seed": args.seed,
                    "mode": args.mode,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        logger.info("sampling_done", tribunal=tribunal, n=len(samples), path=str(out_path))
        print(f"Sampled {len(samples)} texts for {tribunal} -> {out_path}")

        if args.all:
            time.sleep(1)

    suffix = f"_{args.mode}" if args.mode != "sentenca" else ""
    manifest_path = output_dir / f"sample_summary{suffix}.json"
    manifest_path.write_text(
        json.dumps(
            {"seed": args.seed, "mode": args.mode, "tribunals": summary},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    ok = sum(1 for v in summary.values() if v["status"] == "ok")
    empty = sum(1 for v in summary.values() if v["status"] == "empty")
    print(f"\nDone: {ok} tribunals sampled, {empty} empty. Summary manifest: {manifest_path}")

    if not args.all and ok == 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
