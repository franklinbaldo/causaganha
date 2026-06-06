"""Sample judicial decision texts from Internet Archive for segmenter annotation.

Fetches individual JSON files directly from inside IA ZIP items (no full
ZIP download).  Each inner JSON contains ~1000 intimações.  Records are
filtered by document type and scored by rare-class cue density to
prioritize docs that exercise the v7 ontology's underrepresented categories.

Inner JSONs within a ZIP are selected randomly (seeded) to avoid the
ordering bias that comes from always picking the first page.

Usage:
    # One random JSON per tribunal (all tiers)
    uv run python scripts/sample_ia_texts.py --all

    # Single tribunal
    uv run python scripts/sample_ia_texts.py --tribunal TJRO

    # Acórdão-targeted mode (filters for collegiate bodies)
    uv run python scripts/sample_ia_texts.py --all --mode acordao
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

DECISION_TYPES = {"Sentença", "Decisão", "Acórdão"}

COLLEGIATE_ORGAN = re.compile(
    r"Turma\b|C[âa]mara\b|Se[çc][ãa]o\b|Plen[áa]rio",
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
    """Find IA items for a tribunal via advanced search."""
    url = IA_SEARCH_URL.format(tribunal=tribunal.lower())
    with urlopen(url, timeout=30) as r:
        data = json.loads(r.read())
    items = [d["identifier"] for d in data.get("response", {}).get("docs", [])]
    logger.info("discovered_items", tribunal=tribunal, count=len(items))
    return items


def list_zips(item_id: str) -> list[tuple[str, int]]:
    """List ZIP files in an IA item with their inner file counts."""
    url = f"https://archive.org/metadata/{item_id}/files"
    with urlopen(url, timeout=30) as r:
        files = json.loads(r.read()).get("result", [])
    return [(f["name"], int(f.get("filecount", 1))) for f in files if f["name"].endswith(".zip")]


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
    if isinstance(data, dict):
        return data.get("items", [data])
    if isinstance(data, list):
        return data
    return []


def score_record(texto: str) -> tuple[dict[str, bool], int]:
    """Score a text by rare-class cue presence."""
    hits = {name: bool(pat.search(texto)) for name, pat in RARE_CLASS_CUES.items()}
    return hits, sum(hits.values())


def _filter_and_score(
    records: list[dict],
    tribunal: str,
    item_id: str,
    zip_name: str,
    json_name: str,
    mode: str,
) -> list[dict]:
    """Apply structured gate + regex scoring to raw records."""
    filtered: list[dict] = []
    seen: set[str] = set()
    for rec in records:
        if not isinstance(rec, dict):
            continue
        texto = (rec.get("texto") or "").strip()
        if len(texto) < 200:
            continue

        h = hashlib.sha256(texto.encode()).hexdigest()
        if h in seen:
            continue
        seen.add(h)

        tipo = (rec.get("tipoDocumento") or "").strip()
        orgao = (rec.get("nomeOrgao") or "").strip()

        if mode == "acordao":
            is_collegiate = bool(COLLEGIATE_ORGAN.search(orgao))
            has_acordam = bool(re.search(r"\bACORDAM\b", texto))
            if not (is_collegiate or has_acordam):
                continue
        elif tipo and tipo not in DECISION_TYPES:
            continue

        cue_hits, cue_score = score_record(texto)

        filtered.append(
            {
                "text": texto,
                "info": {
                    "id": str(rec.get("id", "")),
                    "tribunal": tribunal,
                    "tipoDocumento": tipo,
                    "nomeOrgao": orgao,
                    "nomeClasse": (rec.get("nomeClasse") or "").strip(),
                    "source_item": item_id,
                    "source_zip": zip_name,
                    "source_json": json_name,
                    "sha256": h,
                },
                "cue_hits": cue_hits,
                "cue_score": cue_score,
            }
        )
    return filtered


def sample_tribunal(tribunal: str, seed: int, mode: str) -> list[dict]:
    """Fetch one random inner JSON for a tribunal, filter and score records."""
    items = discover_items(tribunal)
    if not items:
        logger.warning("no_items_found", tribunal=tribunal)
        return []

    rng = random.Random(seed)
    rng.shuffle(items)

    for item_id in items:
        try:
            zips = list_zips(item_id)
        except (URLError, TimeoutError, OSError) as e:
            logger.warning("list_zips_failed", item=item_id, error=str(e))
            continue

        trib_zips = [(z, c) for z, c in zips if tribunal.upper() in z.upper()]
        if not trib_zips:
            continue

        # Prefer multi-file ZIPs (more inner JSONs → better randomisation)
        multi = [(z, c) for z, c in trib_zips if c > 1]
        pool = multi or trib_zips
        rng.shuffle(pool)

        for zip_name, _filecount in pool:
            try:
                inner_jsons = list_inner_jsons(item_id, zip_name)
            except (URLError, TimeoutError, OSError) as e:
                logger.warning("list_jsons_failed", zip=zip_name, error=str(e))
                continue

            if not inner_jsons:
                continue

            json_name = rng.choice(inner_jsons)

            try:
                records = fetch_json_records(item_id, zip_name, json_name)
            except (URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
                logger.warning("fetch_failed", json=json_name, error=str(e))
                continue

            filtered = _filter_and_score(
                records,
                tribunal,
                item_id,
                zip_name,
                json_name,
                mode,
            )

            if filtered:
                filtered.sort(key=lambda r: r["cue_score"], reverse=True)
                logger.info(
                    "sampled",
                    tribunal=tribunal,
                    raw=len(records),
                    kept=len(filtered),
                    top_score=filtered[0]["cue_score"],
                    source=f"{item_id}/{zip_name}/{json_name}",
                )
                return filtered

            logger.info(
                "no_decisions",
                zip=zip_name,
                json=json_name,
                raw=len(records),
            )

    logger.warning("no_suitable_records", tribunal=tribunal)
    return []


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sample texts from IA for segmenter annotation",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tribunal", help="Tribunal sigla (e.g. TJRO)")
    group.add_argument("--all", action="store_true", help="All tribunals")
    parser.add_argument(
        "--mode",
        choices=["sentenca", "acordao"],
        default="sentenca",
        help="sentenca: Sentença/Decisão types; acordao: collegiate bodies",
    )
    parser.add_argument("--output-dir", default="data/segmenter_samples")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tribunals = ALL_TRIBUNALS if args.all else [args.tribunal.upper()]

    summary: dict[str, dict] = {}
    for tribunal in tribunals:
        logger.info("sampling_start", tribunal=tribunal, mode=args.mode)
        records = sample_tribunal(tribunal, args.seed, args.mode)

        if not records:
            summary[tribunal] = {"status": "empty", "n": 0}
            continue

        suffix = f"_{args.mode}" if args.mode != "sentenca" else ""
        out_path = output_dir / f"{tribunal.lower()}{suffix}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        summary[tribunal] = {
            "status": "ok",
            "n": len(records),
            "top_score": records[0]["cue_score"],
            "source": records[0]["info"]["source_item"],
            "path": str(out_path),
        }

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
    print(f"\nDone: {ok} tribunals sampled, {empty} empty. Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
