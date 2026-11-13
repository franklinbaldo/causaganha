#!/usr/bin/env python3
"""Incremental CNJ locator for DJEN ZIP originals preserved at Internet Archive.

No protobuf/Parquet copy is produced. The index is rebuildable from original ZIPs.
Use one IA item per invocation (e.g. djen-tjro-2026). Unavailable ZIPs are
NOT interpreted as absence of communications.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import httpx

from causaganha.consolidate.zip_processor import (
    MAX_DOWNLOAD_BYTES,
    MAX_TOTAL_UNCOMPRESSED_BYTES,
    MAX_ZIP_MEMBERS,
    ZipBudgetExceededError,
    _check_member_budget,
)

ITEM_RE = re.compile(r"^djen-([a-z0-9]+)-(20[0-9]{2})$")
ZIP_RE = re.compile(r"^djen-(20[0-9]{2}-[0-9]{2}-[0-9]{2})-([A-Z0-9]+)\.zip$")
CNJ_RE = re.compile(r"^[0-9]{20}$")


def records_of(data: object) -> list[dict]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return [r for r in items if isinstance(r, dict)]
        if "numero_processo" in data:
            return [data]
    return []


def extract_locations(zip_path: Path, *, item: str, filename: str) -> dict[str, list[dict]]:
    """Read each JSON member exactly once; locate records by CNJ and hash/ID."""
    result: dict[str, list[dict]] = defaultdict(list)
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        if len(infos) > MAX_ZIP_MEMBERS:
            raise ZipBudgetExceededError("Too many ZIP members")
        total = 0
        for info in infos:
            if not info.filename.endswith(".json"):
                continue
            _check_member_budget(info, zip_path)
            total += info.file_size
            if total > MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise ZipBudgetExceededError("ZIP cumulative size exceeded")
            with zf.open(info) as stream:
                data = json.load(stream)
            for record in records_of(data):
                cnj = str(record.get("numero_processo") or "")
                if not CNJ_RE.fullmatch(cnj):
                    continue
                result[cnj].append({
                    "item": item,
                    "zip": filename,
                    "member": info.filename,
                    "id": record.get("id"),
                    "hash": record.get("hash"),
                })
    return dict(result)


def index_file(out_dir: Path, partition: str) -> Path:
    return out_dir / f"{partition}.json"


def merge_zip(index: dict, *, filename: str, fingerprint: str, rows: dict[str, list[dict]]) -> None:
    """Replace entries for a changed ZIP atomically in the in-memory index."""
    index.setdefault("sources", {})[filename] = fingerprint
    items = index.setdefault("processos", {})
    for cnj in list(items):
        remaining = [entry for entry in items[cnj] if entry["zip"] != filename]
        if remaining:
            items[cnj] = remaining
        else:
            del items[cnj]
    for cnj, entries in rows.items():
        items.setdefault(cnj, []).extend(entries)
    for entries in items.values():
        entries.sort(key=lambda r: (r["zip"], r["member"], str(r["id"])))


def load_index(path: Path, *, item: str) -> dict:
    if not path.exists():
        return {"version": 1, "item": item, "sources": {}, "processos": {}}
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("version") != 1 or doc.get("item") != item:
        raise ValueError(f"Incompatible index in {path}")
    return doc


def save_index(path: Path, index: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(index, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    staged = path.with_suffix(".tmp")
    staged.write_text(content, encoding="utf-8")
    staged.replace(path)


def run(item: str, out_dir: Path, max_zips: int) -> int:
    match = ITEM_RE.fullmatch(item)
    if not match:
        raise ValueError(f"Invalid IA item ID: {item}")
    tribunal, year = match.groups()
    partition = f"{tribunal}_{year}"
    path = index_file(out_dir, partition)
    index = load_index(path, item=item)
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        response = client.get(f"https://archive.org/metadata/{item}/files")
        response.raise_for_status()
        remote = response.json()
        files = remote.get("result", remote)
        if not isinstance(files, list):
            raise ValueError("Unexpected IA files response")
        candidates = []
        for f in files:
            if not isinstance(f, dict):
                continue
            name = f.get("name", "")
            m = ZIP_RE.fullmatch(name)
            if m and m.group(2).lower() == tribunal and m.group(1).startswith(year):
                fingerprint = f.get("md5") or f.get("sha1") or f.get("size")
                if not fingerprint:
                    # Missing metadata is not grounds for silently skipping an update.
                    fingerprint = "unknown"
                if index["sources"].get(name) != str(fingerprint):
                    candidates.append((name, str(fingerprint)))
        # Most recent first; bounded incremental backfill at each daily run.
        candidates.sort(reverse=True)
        changed = 0
        for name, fingerprint in candidates[:max_zips]:
            url = f"https://archive.org/download/{quote(item)}/{quote(name)}"
            with tempfile.TemporaryDirectory() as td:
                target = Path(td) / name
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    downloaded = 0
                    with target.open("wb") as fd:
                        for chunk in response.iter_bytes():
                            downloaded += len(chunk)
                            if downloaded > MAX_DOWNLOAD_BYTES:
                                raise ZipBudgetExceededError("ZIP download exceeds budget")
                            fd.write(chunk)
                rows = extract_locations(target, item=item, filename=name)
            merge_zip(index, filename=name, fingerprint=fingerprint, rows=rows)
            changed += 1
        if changed:
            save_index(path, index)
        print(json.dumps({"item": item, "indexed_zips": changed,
                          "pending_zips": max(0, len(candidates) - changed),
                          "processos": len(index["processos"])}))
        return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item", required=True, help="djen-tjro-2026")
    parser.add_argument("--output", type=Path, default=Path("web/public/indexes/djen-raw"))
    parser.add_argument("--max-zips", type=int, default=5)
    args = parser.parse_args()
    if args.max_zips < 1:
        parser.error("--max-zips must be >= 1")
    run(args.item, args.output, args.max_zips)


if __name__ == "__main__":
    main()
