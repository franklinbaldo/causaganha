#!/usr/bin/env python3
"""Index original DJEN ZIPs as per-process CSVs inside year/forum ZIP partitions.

The original DJEN archives stay immutable in IA. Derived index ZIPs are
replaceable. Every run processes a bounded set of new/changed original ZIPs.
"""

from __future__ import annotations

import argparse
import json
import re
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

import httpx

from causaganha.consolidate.process_pointer_pb import (
    decode_index,
    encode_index,
    update_datajud,
)
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
PARTITION_RE = re.compile(r"^([0-9]{4})_([0-9]{4})\.zip$")
INDEX_BASE = "https://archive.org/download"
INDEX_PREFIX = "causaganha-index-"
MAX_PARTITIONS_PER_ITEM = 1000
HEADER = ("data", "membro", "id", "hash")


def index_item(tribunal: str, process_year: str) -> str:
    """One IA item per tribunal and filing year."""
    cnj_court = {"tjro": "8-22"}[tribunal]
    return f"causaganha-{process_year}-{cnj_court}"


def control_item(tribunal: str) -> str:
    """Manifest separate from original DJEN ZIPs and derived ZIP partitions."""
    return f"{INDEX_PREFIX}control-{tribunal}"


def remote_partition_name(partition: str) -> str:
    match = PARTITION_RE.fullmatch(partition)
    if not match:
        raise ValueError(f"Invalid index partition: {partition}")
    return f"{match.group(2)}.zip"


def partition_for(cnj: str) -> str:
    if not CNJ_RE.fullmatch(cnj):
        raise ValueError(f"Invalid CNJ: {cnj!r}")
    return f"{cnj[9:13]}_{cnj[16:20]}.zip"


def short_cnj_filename(cnj: str) -> str:
    """The other 11 CNJ digits live in the IA item and origin ZIP path."""
    if not CNJ_RE.fullmatch(cnj):
        raise ValueError(f"Invalid CNJ: {cnj!r}")
    return f"{cnj[:9]}.csv"


def expand_cnj_filename(filename: str, partition: Path, *, court: str = "822") -> str:
    """Recover the full CNJ from a nine-digit name and partition coordinates."""
    match = PARTITION_RE.fullmatch(partition.name)
    if not match or not re.fullmatch(r"[0-9]{9}\.csv", filename):
        raise ValueError(f"Invalid index member or partition: {partition}/{filename}")
    if not re.fullmatch(r"[0-9]{3}", court):
        raise ValueError("Invalid justice/tribunal digits")
    year, origin = match.groups()
    return f"{filename[:9]}{year}{court}{origin}"


def records_of(value: object) -> list[dict]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        if isinstance(value.get("items"), list):
            return [row for row in value["items"] if isinstance(row, dict)]
        if "numero_processo" in value:
            return [value]
    return []


def extract_locations(
    zip_path: Path, *, filename: str
) -> dict[str, list[tuple[str, str, str, str]]]:
    """Return CNJ -> (publication date, JSON member, ID, DJEN hash)."""
    match = ZIP_RE.fullmatch(filename)
    if not match:
        raise ValueError(f"Unexpected DJEN file name: {filename}")
    publication_date = match.group(1)
    rows: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    with zipfile.ZipFile(zip_path) as archive:
        infos = archive.infolist()
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
            with archive.open(info) as stream:
                contents = json.load(stream)
            for record in records_of(contents):
                cnj = str(record.get("numero_processo") or "")
                if not CNJ_RE.fullmatch(cnj):
                    continue
                record_id = record.get("id")
                record_hash = record.get("hash")
                if record_id is None or not isinstance(record_hash, str) or not record_hash:
                    raise ValueError(f"Missing DJEN identity for CNJ {cnj}")
                rows[cnj].append((publication_date, info.filename, str(record_id), record_hash))
    return dict(rows)


def load_partition(zip_path: Path) -> dict[str, dict]:
    """Read PB members keyed by CNJ reconstructed from the partition."""
    if not zip_path.exists():
        return {}
    result: dict[str, dict] = {}
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if not re.fullmatch(r"[0-9]{9}\.pb", info.filename):
                raise ValueError(f"Unexpected index ZIP member: {info.filename}")
            cnj = expand_cnj_filename(info.filename[:-3] + ".csv", zip_path)
            if cnj in result:
                raise ValueError(f"Duplicate CNJ index member: {info.filename}")
            result[cnj] = decode_index(archive.read(info))
    return result


def write_partition(path: Path, data: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(".part")
    with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for cnj, pointer in sorted(data.items()):
            if partition_for(cnj) != path.name or cnj[13:16] != "822":
                raise ValueError(f"CNJ does not belong in index partition: {cnj}")
            pubs = pointer["publicacoes"]
            snapshots = pointer["datajud"]
            if pubs or snapshots:
                name = short_cnj_filename(cnj).removesuffix(".csv") + ".pb"
                archive.writestr(name, encode_index(pubs, snapshots))
    staged.replace(path)


def merge_datajud(partition: dict[str, dict], rows: dict[str, list[dict[str, str]]]) -> bool:
    """Update the latest DataJud pointer per document identity."""
    changed = False
    for cnj, incoming in rows.items():
        current = partition.setdefault(cnj, {"publicacoes": [], "datajud": []})
        updated = update_datajud(current["datajud"], incoming)
        if updated != current["datajud"]:
            current["datajud"] = updated
            changed = True
    return changed


def load_datajud_locators(path: Path) -> dict[str, list[dict[str, str]]]:
    """Read explicit per-document DataJud ZIP locators from an optional JSONL feed."""
    required = {
        "tribunal",
        "grau",
        "documento_id",
        "item_ia",
        "arquivo_zip",
        "membro",
        "atualizado_em",
    }
    records: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            entry = json.loads(line)
            cnj = entry.get("numero_processo")
            if not isinstance(cnj, str) or not CNJ_RE.fullmatch(cnj):
                raise ValueError("Invalid DataJud CNJ locator")
            if not all(isinstance(entry.get(field), str) and entry[field] for field in required):
                raise ValueError("Incomplete DataJud locator; no implicit item/ZIP guesses")
            records[cnj].append({field: entry[field] for field in required})
    return dict(records)


def apply_source(
    partition: dict[str, dict],
    *,
    publication_date: str,
    new_rows: dict[str, list[tuple[str, str, str, str]]],
) -> bool:
    """Replace publications of one source date; preserve DataJud pointers."""
    before = {cnj: list(pointer["publicacoes"]) for cnj, pointer in partition.items()}
    for cnj in list(partition):
        pointer = partition[cnj]
        pointer["publicacoes"] = [
            row for row in pointer["publicacoes"] if row[0] != publication_date
        ]
        if not pointer["publicacoes"] and not pointer["datajud"]:
            del partition[cnj]
    for cnj, rows in new_rows.items():
        if not rows:
            continue
        current = partition.setdefault(cnj, {"publicacoes": [], "datajud": []})
        current["publicacoes"] = sorted(set(current["publicacoes"] + rows))
    if set(partition) != set(before):
        return True
    return any(partition[cnj]["publicacoes"] != before[cnj] for cnj in partition)


def download(client: httpx.Client, url: str, target: Path) -> bool:
    with client.stream("GET", url) as response:
        if response.status_code == 404:
            return False
        response.raise_for_status()
        size = 0
        with target.open("wb") as handle:
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > MAX_DOWNLOAD_BYTES:
                    raise ZipBudgetExceededError(f"Download exceeds budget: {url}")
                handle.write(chunk)
    return True


def run(
    item: str,
    output: Path,
    max_zips: int,
    *,
    restore_remote: bool = False,
    datajud_locators: Path | None = None,
    datajud_from_ia: bool = False,
    max_datajud_files: int = 5,
) -> dict:
    match = ITEM_RE.fullmatch(item)
    if not match:
        raise ValueError("Invalid DJEN tribunal/year item")
    tribunal, year = match.groups()
    target_item = control_item(tribunal)
    output.mkdir(parents=True, exist_ok=True)
    manifest_file = output / f"{tribunal}_manifest.json"
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        if restore_remote:
            download(client, f"{INDEX_BASE}/{target_item}/manifest.json", manifest_file)
        manifest = (
            json.loads(manifest_file.read_text(encoding="utf-8"))
            if manifest_file.exists()
            else {
                "version": 4,
                "tribunal": tribunal,
                "sources": {},
                "partitions": [],
                "source_partitions": {},
            }
        )
        if manifest.get("version") != 4 or manifest.get("tribunal") != tribunal:
            raise ValueError("Incompatible index manifest")
        response = client.get(f"https://archive.org/metadata/{item}/files")
        response.raise_for_status()
        listing = response.json()
        files = listing.get("result", listing)
        if not isinstance(files, list):
            msg = "Unexpected IA file listing"
            raise TypeError(msg)
        candidates = []
        for info in files:
            if not isinstance(info, dict):
                continue
            filename = str(info.get("name", ""))
            parsed = ZIP_RE.fullmatch(filename)
            if not parsed or parsed.group(2).lower() != tribunal:
                continue
            if not parsed.group(1).startswith(year):
                continue
            fingerprint = info.get("sha1") or info.get("md5")
            # Unknown fingerprint is intentionally always rechecked.
            if not fingerprint or manifest["sources"].get(filename) != fingerprint:
                candidates.append((filename, fingerprint))
        candidates.sort(reverse=True)
        loaded: dict[str, dict] = {}
        touched: set[str] = set()
        known_partitions = set(manifest["partitions"])
        source_partitions = manifest.setdefault("source_partitions", {})

        def get_partition(partition_name: str) -> dict:
            if partition_name not in loaded:
                path = output / partition_name
                if restore_remote and partition_name in known_partitions:
                    if not download(
                        client,
                        f"{INDEX_BASE}/{index_item(tribunal, partition_name[:4])}/{remote_partition_name(partition_name)}",
                        path,
                    ):
                        raise FileNotFoundError(f"Missing indexed partition {path}")
                loaded[partition_name] = load_partition(path)
            return loaded[partition_name]

        for filename, fingerprint in candidates[:max_zips]:
            with tempfile.TemporaryDirectory() as directory:
                original = Path(directory) / filename
                if not download(client, f"{INDEX_BASE}/{item}/{filename}", original):
                    raise FileNotFoundError(f"Original ZIP disappeared: {filename}")
                records = extract_locations(original, filename=filename)
            by_partition: dict[str, dict[str, list[tuple[str, str, str, str]]]] = defaultdict(dict)
            for cnj, rows in records.items():
                by_partition[partition_for(cnj)][cnj] = rows
            publication_date = ZIP_RE.fullmatch(filename).group(1)
            # A changed original may have removed processes in any old partition.
            # Iterate every known partition plus all partitions in the new source.
            former = source_partitions.get(filename)
            affected = (
                known_partitions | set(by_partition)
                if filename in manifest["sources"] and former is None
                else set(former or []) | set(by_partition)
            )
            for part_name in sorted(affected):
                data = get_partition(part_name)
                if apply_source(
                    data,
                    publication_date=publication_date,
                    new_rows=by_partition.get(part_name, {}),
                ):
                    touched.add(part_name)
                if data:
                    known_partitions.add(part_name)
            manifest["sources"][filename] = fingerprint
            source_partitions[filename] = sorted(by_partition)
        # Collect independent source-confirmed DataJud locator sidecars.
        # A sidecar is written *after* its snapshot ZIP and contains exact member names.
        feeds: list[Path] = [datajud_locators] if datajud_locators else []
        processed_datajud: dict[str, str] = {}
        if datajud_from_ia:
            datajud_item = f"datajud-{tribunal}"
            response = client.get(f"https://archive.org/metadata/{datajud_item}/files")
            if response.status_code != 404:
                response.raise_for_status()
                listing = response.json()
                ia_files = listing.get("result", listing)
                if not isinstance(ia_files, list):
                    raise ValueError("Malformed DataJud IA inventory")
                datajud_seen = manifest.setdefault("datajud_sources", {})
                available = []
                for info in ia_files:
                    if not isinstance(info, dict):
                        continue
                    name = info.get("name", "")
                    if not re.fullmatch(
                        rf"{re.escape(tribunal)}_20[0-9]{{2}}-[0-9]{{2}}-[0-9]{{2}}\\.locators\\.jsonl",
                        name,
                    ):
                        continue
                    checksum = info.get("sha1") or info.get("md5")
                    if not checksum:
                        continue
                    if name in datajud_seen and datajud_seen[name] != checksum:
                        raise ValueError(
                            f"Changed DataJud sidecar {name}: explicit rebuild required"
                        )
                    if name not in datajud_seen:
                        available.append((name, str(checksum)))
                available.sort()
                for name, checksum in available[:max_datajud_files]:
                    local = output / name
                    if not download(client, f"{INDEX_BASE}/{datajud_item}/{name}", local):
                        raise FileNotFoundError(f"Missing DataJud locator: {name}")
                    feeds.append(local)
                    processed_datajud[name] = checksum

        datajud_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
        for feed in feeds:
            for cnj, snapshots in load_datajud_locators(feed).items():
                datajud_rows[cnj].extend(snapshots)
        dj_by_partition: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(dict)
        for cnj, snapshots in datajud_rows.items():
            if cnj[13:16] == "822":
                dj_by_partition[partition_for(cnj)][cnj] = snapshots
        for part_name, rows in dj_by_partition.items():
            partition = get_partition(part_name)
            if merge_datajud(partition, rows):
                touched.add(part_name)
                known_partitions.add(part_name)
        manifest.setdefault("datajud_sources", {}).update(processed_datajud)
        counts: dict[str, int] = defaultdict(int)
        for part_name in known_partitions:
            counts[part_name[:4]] += 1
        if any(count > MAX_PARTITIONS_PER_ITEM for count in counts.values()):
            raise ValueError("IA filing-year index item exceeds 1000-partition policy")
        for part_name in sorted(touched):
            write_partition(output / part_name, loaded[part_name])
        processed = min(len(candidates), max_zips)
        if processed or touched or processed_datajud:
            manifest["partitions"] = sorted(known_partitions)
            staged = manifest_file.with_suffix(".tmp")
            staged.write_text(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            staged.replace(manifest_file)
        return {
            "source_item": item,
            "index_item": target_item,
            "tribunal": tribunal,
            "source_year": year,
            "indexed_zips": processed,
            "pending_zips": max(0, len(candidates) - processed),
            "changed_partitions": len(touched),
            "processed_datajud_files": len(processed_datajud),
            "publish_files": sorted(touched)
            + (["manifest.json"] if processed or touched or processed_datajud else []),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item", default="djen-tjro-2026")
    parser.add_argument("--output", type=Path, default=Path("data/djen-cnj-index"))
    parser.add_argument("--max-zips", type=int, default=5)
    parser.add_argument("--restore-remote", action="store_true")
    parser.add_argument("--datajud-locators", type=Path, help="Optional DataJud JSONL pointer feed")
    parser.add_argument("--datajud-from-ia", action="store_true")
    parser.add_argument("--max-datajud-files", type=int, default=5)
    args = parser.parse_args()
    if args.max_zips < 1:
        parser.error("--max-zips must be positive")
    print(
        json.dumps(
            run(
                args.item,
                args.output,
                args.max_zips,
                restore_remote=args.restore_remote,
                datajud_locators=args.datajud_locators,
                datajud_from_ia=args.datajud_from_ia,
                max_datajud_files=args.max_datajud_files,
            )
        )
    )


if __name__ == "__main__":
    main()
