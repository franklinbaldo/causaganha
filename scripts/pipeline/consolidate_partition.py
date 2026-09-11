"""Run the existing tribunal/year converter against a verified Archive inventory."""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from pathlib import Path

import httpx

from scripts.pipeline.archive_partitions import RECEIPT, inventory
from scripts.pipeline.ia_s3 import create_upload_client, get_ia_s3_auth, upload_to_ia


def sync_entries(snapshot: dict) -> dict:
    """Adapt physical inventory to the existing converter's input contract."""
    return {
        entry["name"][5:15]: [
            {
                "filename": entry["name"],
                "item_id": snapshot["item"],
                "tribunal": snapshot["tribunal"],
                "absent": False,
                "md5": entry["md5"],
                "size": entry["size"],
            }
        ]
        for entry in snapshot["inputs"]
    }


async def publish_receipt(item: str, receipt: dict) -> None:
    auth = get_ia_s3_auth()
    if not auth:
        message = "Archive credentials required"
        raise RuntimeError(message)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / RECEIPT
        path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
        async with create_upload_client(auth) as client:
            uploaded = await upload_to_ia(client, item, path, f"{receipt['year']}-01-01")
        if not uploaded:
            message = "Receipt upload failed"
            raise RuntimeError(message)


def run(item: str, *, dry_run: bool = False) -> None:
    from scripts.pipeline.consolidate import TABLES, consolidate_tribunal_year

    if not dry_run and not get_ia_s3_auth():
        message = "Archive credentials required"
        raise RuntimeError(message)
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        before = inventory(client, item)
        if not before["inputs"]:
            message = "Partition has no ZIPs"
            raise ValueError(message)
        checksums: dict[str, str] = {}
        stats = consolidate_tribunal_year(
            before["tribunal"],
            before["year"],
            sync_entries(before),
            dry_run=dry_run,
            output_checksums=checksums,
        )
        if dry_run:
            print(json.dumps(stats))
            return
        after = inventory(client, item)
        if after["fingerprint"] != before["fingerprint"]:
            message = "ZIP inventory changed during consolidation; retry required"
            raise RuntimeError(message)
        outputs = []
        stale = {
            entry["name"]
            for entry in after["files"]
            if entry["name"] in {f"{table}.parquet" for table in TABLES}
        } - checksums.keys()
        if stale:
            message = f"Obsolete Parquets must be resolved before certification: {sorted(stale)}"
            raise RuntimeError(message)
        for entry in after["files"]:
            if entry["name"] not in checksums:
                continue
            if entry.get("md5") != checksums[entry["name"]]:
                message = "Output checksum differs from the generated Parquet"
                raise ValueError(message)
            url = f"https://archive.org/download/{item}/{entry['name']}"
            with client.stream("GET", url, headers={"Range": "bytes=0-3"}) as response:
                if response.status_code != 206 or response.read() != b"PAR1":
                    message = f"Parquet read-back failed: {url}"
                    raise RuntimeError(message)
            outputs.append({"name": entry["name"], "md5": entry["md5"]})
        if len(outputs) < stats["uploaded"] or not outputs:
            message = "Published inventory does not contain all outputs"
            raise RuntimeError(message)
        receipt = {key: value for key, value in before.items() if key != "files"}
        receipt["outputs"] = outputs
        asyncio.run(publish_receipt(item, receipt))
        response = client.get(f"https://archive.org/download/{item}/{RECEIPT}")
        response.raise_for_status()
        if response.json() != receipt:
            message = "Receipt read-back mismatch"
            raise RuntimeError(message)
        print(json.dumps(stats))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.item, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
