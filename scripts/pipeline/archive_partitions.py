"""Discover consolidation partitions from Archive metadata, independently of collection state."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import httpx

from causaganha.consolidate.schema_registry import CURRENT_VERSION


ITEM = re.compile(r"djen-([a-z0-9-]+)-(20\d{2})")
RECEIPT = "consolidation-inputs.json"
# Bump when transformation/output semantics change without a schema change.
REVISION = "1"


def inventory(client: httpx.Client, item: str) -> dict:
    """Fail closed on an unavailable/malformed inventory; never interpret it as empty."""
    match = ITEM.fullmatch(item)
    if not match:
        message = f"Invalid tribunal/year item: {item}"
        raise ValueError(message)
    response = client.get(f"https://archive.org/metadata/{item}")
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        message = f"Incomplete Archive metadata: {item}"
        raise TypeError(message)
    tribunal, year = match.groups()
    pattern = re.compile(rf"djen-({year}-\d{{2}}-\d{{2}})-{re.escape(tribunal.upper())}\.zip")
    inputs = []
    for entry in data["files"]:
        name = entry["name"]
        if pattern.fullmatch(name):
            if not entry.get("md5") or int(entry.get("size", 0)) <= 0:
                message = f"Missing ZIP integrity metadata: {item}/{name}"
                raise ValueError(message)
            inputs.append({"name": name, "size": int(entry["size"]), "md5": entry["md5"]})
    inputs.sort(key=lambda entry: entry["name"])
    payload = {"inputs": inputs, "schema": CURRENT_VERSION, "revision": REVISION}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {
        "item": item,
        "tribunal": tribunal.upper(),
        "year": int(year),
        "fingerprint": fingerprint,
        **payload,
        "files": data["files"],
    }


def needs_consolidation(client: httpx.Client, snapshot: dict) -> bool:
    if not snapshot["inputs"]:
        return False
    files = {entry["name"]: entry for entry in snapshot["files"]}
    if RECEIPT not in files:
        return True
    response = client.get(f"https://archive.org/download/{snapshot['item']}/{RECEIPT}")
    response.raise_for_status()
    receipt = response.json()
    if receipt.get("fingerprint") != snapshot["fingerprint"]:
        return True
    outputs = receipt.get("outputs", [])
    return not outputs or any(
        files.get(entry["name"], {}).get("md5") != entry["md5"] for entry in outputs
    )


def discover(client: httpx.Client) -> list[str]:
    items = set()
    page = 1
    while True:
        response = client.get(
            "https://archive.org/advancedsearch.php",
            params={
                "q": "identifier:djen-*",
                "fl[]": "identifier",
                "output": "json",
                "rows": 500,
                "page": page,
                "sort[]": "identifier asc",
            },
        )
        response.raise_for_status()
        result = response.json()["response"]
        docs = result["docs"]
        items.update(doc["identifier"] for doc in docs if ITEM.fullmatch(doc["identifier"]))
        if page * 500 >= int(result["numFound"]):
            break
        if not docs:
            message = "Truncated Archive discovery"
            raise ValueError(message)
        page += 1
    return sorted(items)


def plan(client: httpx.Client, item: str | None, limit: int) -> list[dict]:
    items = [item] if item else discover(client)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {value: pool.submit(inventory, client, value) for value in items}
        pending = []
        errors = []
        for value, future in futures.items():
            try:
                snapshot = future.result()
                if needs_consolidation(client, snapshot):
                    pending.append(snapshot)
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as error:
                if item:
                    raise
                errors.append(value)
                print(f"::warning::Inventory unavailable for {value}: {error}", file=sys.stderr)
    if errors and not pending:
        message = "No runnable partitions; some Archive inventories could not be verified"
        raise RuntimeError(message)
    # Missing/changed receipts remain eligible next run; no permanent 'done' marker.
    pending.sort(key=lambda snapshot: (-snapshot["year"], snapshot["item"]))
    return [{"item": snapshot["item"]} for snapshot in pending[:limit]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item")
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.limit <= 256:
        parser.error("limit must be between 1 and 256")
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        print(json.dumps({"include": plan(client, args.item, args.limit)}))


if __name__ == "__main__":
    main()
