#!/usr/bin/env python3
"""Build sharded CNJ locators from original DJEN ZIPs preserved on Internet Archive.

The index stores only file/member/ID/hash locations; not publication text.
Shards are stable SHA-256(CNJ) prefixes (256 shards per tribunal/year).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
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
INDEX_BASE = "https://archive.org/download/causaganha-djen-original-index"


def shard_for(cnj: str) -> str:
    """Stable, uniform partition independent of the digits' legal structure."""
    return hashlib.sha256(cnj.encode("ascii")).hexdigest()[:2]


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
    """Extract only CNJ-to-member references, with the existing ZIP limits."""
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
                result[cnj].append(
                    {
                        "item": item,
                        "zip": filename,
                        "member": info.filename,
                        "id": record.get("id"),
                        "hash": record.get("hash"),
                    }
                )
    return dict(result)


def manifest_path(out_dir: Path, partition: str) -> Path:
    return out_dir / f"{partition}_manifest.json"


def shard_path(out_dir: Path, partition: str, shard: str) -> Path:
    return out_dir / f"{partition}_{shard}.json"


def load_index(path: Path, *, item: str) -> dict:
    if not path.exists():
        return {"version": 2, "item": item, "processos": {}}
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("version") != 2 or doc.get("item") != item:
        raise ValueError(f"Incompatible index in {path}")
    return doc


def save_index(path: Path, index: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(index, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    staged = path.with_suffix(".tmp")
    staged.write_text(content, encoding="utf-8")
    staged.replace(path)


def merge_zip(index: dict, *, filename: str, rows: dict[str, list[dict]]) -> bool:
    """Idempotently replace all entries for one source in one shard."""
    items = index["processos"]
    old = {cnj: list(entries) for cnj, entries in items.items()}
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
    return old != items


def read_remote(url: str, target: Path, *, required: bool = False) -> bool:
    """Restore a shard; a missing previously published file is an error."""
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        response = client.get(url)
        if response.status_code == 404:
            if required:
                raise FileNotFoundError(f"Published index is missing: {url}")
            return False
        response.raise_for_status()
        target.write_bytes(response.content)
        return True


def restore(out_dir: Path, partition: str) -> None:
    """Restore the manifest and only its declared nonempty shards."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_name = f"{partition}_manifest.json"
    manifest_file = out_dir / manifest_name
    if not read_remote(f"{INDEX_BASE}/{manifest_name}", manifest_file):
        return
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    shards = manifest.get("shards")
    if not isinstance(shards, list):
        raise ValueError("Published manifest missing shard list")
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [
            pool.submit(
                read_remote,
                f"{INDEX_BASE}/{partition}_{shard}.json",
                shard_path(out_dir, partition, shard),
                required=True,
            )
            for shard in shards
        ]
        for future in as_completed(futures):
            future.result()


def run(item: str, out_dir: Path, max_zips: int, *, restore_remote: bool = False) -> dict:
    match = ITEM_RE.fullmatch(item)
    if not match:
        raise ValueError(f"Invalid IA item ID: {item}")
    tribunal, year = match.groups()
    partition = f"{tribunal}_{year}"
    if restore_remote:
        restore(out_dir, partition)
    manifest_file = manifest_path(out_dir, partition)
    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    else:
        manifest = {"version": 2, "item": item, "sources": {}, "shards": []}
    if manifest.get("version") != 2 or manifest.get("item") != item:
        raise ValueError("Incompatible source manifest")
    source_fingerprints = manifest["sources"]
    known_shards = set(manifest["shards"])
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        response = client.get(f"https://archive.org/metadata/{item}/files")
        response.raise_for_status()
        remote = response.json()
        files = remote.get("result", remote)
        if not isinstance(files, list):
            raise ValueError("Unexpected IA files response")
        candidates = []
        for file_info in files:
            if not isinstance(file_info, dict):
                continue
            name = file_info.get("name", "")
            parsed = ZIP_RE.fullmatch(name)
            if parsed and parsed.group(2).lower() == tribunal and parsed.group(1).startswith(year):
                fingerprint = file_info.get("md5") or file_info.get("sha1")
                # Missing fingerprint is not treated as a stable unchanged source.
                if not fingerprint or source_fingerprints.get(name) != str(fingerprint):
                    candidates.append((name, str(fingerprint or "unknown")))
        candidates.sort(reverse=True)
        touched: set[str] = set()
        changed = 0
        for name, fingerprint in candidates[:max_zips]:
            url = f"https://archive.org/download/{quote(item)}/{quote(name)}"
            with tempfile.TemporaryDirectory() as temp_dir:
                target = Path(temp_dir) / name
                with client.stream("GET", url) as download:
                    download.raise_for_status()
                    total_bytes = 0
                    with target.open("wb") as handle:
                        for chunk in download.iter_bytes():
                            total_bytes += len(chunk)
                            if total_bytes > MAX_DOWNLOAD_BYTES:
                                raise ZipBudgetExceededError("ZIP download exceeds budget")
                            handle.write(chunk)
                rows = extract_locations(target, item=item, filename=name)
            by_shard: dict[str, dict[str, list[dict]]] = defaultdict(dict)
            for cnj, entries in rows.items():
                by_shard[shard_for(cnj)][cnj] = entries
            # Changed ZIP may have old records in any shard: update all shards.
            for shard in (f"{i:02x}" for i in range(256)):
                path = shard_path(out_dir, partition, shard)
                index = load_index(path, item=item)
                if merge_zip(index, filename=name, rows=by_shard.get(shard, {})):
                    save_index(path, index)
                    touched.add(path.name)
                    known_shards.add(shard)
            source_fingerprints[name] = fingerprint
            changed += 1
        if changed:
            save_index(manifest_file, manifest)
        report = {
            "item": item,
            "indexed_zips": changed,
            "pending_zips": max(0, len(candidates) - changed),
            "shards_changed": len(touched),
            "publish_files": sorted(touched) + ([manifest_file.name] if changed else []),
        }
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item", required=True, help="djen-tjro-2026")
    parser.add_argument("--output", type=Path, default=Path("web/public/indexes/djen-raw"))
    parser.add_argument("--max-zips", type=int, default=5)
    parser.add_argument("--restore-remote", action="store_true")
    args = parser.parse_args()
    if args.max_zips < 1:
        parser.error("--max-zips must be >= 1")
    print(json.dumps(run(args.item, args.output, args.max_zips, restore_remote=args.restore_remote)))


if __name__ == "__main__":
    main()
