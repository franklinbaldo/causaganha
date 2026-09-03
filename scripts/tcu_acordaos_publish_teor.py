#!/usr/bin/env python3
"""Publish the materialized TCU TEOR Parquet to Internet Archive, with read-back proof.

Purpose:  #1022 needs an observable public URL for the #1020 materialization, with proof
          that the bytes readable at that URL match what was produced locally — not just a
          successful upload response.
Strategy: Upload the given local Parquet to the tcu-acordaos-2017-2026 IA item via
          tcu_acordaos.publish.publish_parquet, then independently re-download it and verify
          checksum/schema/row-count with tcu_acordaos.publish.verify_published. Only a run
          whose read-back proof passes every check is recorded as "published" in the
          evidence report; a failed upload or a failed proof is written to the same report
          shape with published=False, exactly to prevent silently promoting the year to
          "published" on a green HTTP status alone (#1022 risk: "confundir sucesso HTTP do
          PUT com publicação verificável").
Status:   one-off publish step, run manually with real IA_ACCESS_KEY/IA_SECRET_KEY and a
          real materialized Parquet. Not part of any CI job — mirrors
          scripts/tcu_acordaos_prove_bulk.py's convention.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from tcu_acordaos.publish import ITEM_ID, REMOTE_NAME, publish_parquet, verify_published


def build_evidence(
    *,
    parquet_path: Path,
    uploaded: bool,
    proof: Any,
) -> dict:
    """Assemble the JSON-serializable evidence report. Pure — no I/O."""
    return {
        "item_id": ITEM_ID,
        "remote_name": REMOTE_NAME,
        "local_parquet": str(parquet_path),
        "upload_succeeded": uploaded,
        "read_back": {
            "url": proof.url,
            "size_bytes": proof.size_bytes,
            "sha256": proof.sha256,
            "record_count": proof.record_count,
            "checksum_matches_local": proof.checksum_matches_local,
            "schema_ok": proof.schema_ok,
            "count_matches_local": proof.count_matches_local,
        },
        "published": bool(uploaded and proof.published),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--parquet",
        type=Path,
        required=True,
        help="Path to the locally materialized TCU TEOR Parquet (tcu_acordaos.materialize output)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/data/tcu-acordaos-publish-proof.json"),
        help="Where to write the JSON evidence report",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip the PUT and only verify what is already published (reruns/debugging)",
    )
    args = parser.parse_args(argv)

    if not args.parquet.exists():
        print(f"FATAL: {args.parquet} does not exist", file=sys.stderr)
        return 1

    uploaded = True
    if not args.skip_upload:
        ia_key = os.environ.get("IA_ACCESS_KEY", "")
        ia_secret = os.environ.get("IA_SECRET_KEY", "")
        if not (ia_key and ia_secret):
            print(
                "FATAL: IA_ACCESS_KEY/IA_SECRET_KEY not set — refusing to publish without "
                "real credentials (use --skip-upload to only verify an existing publication)",
                file=sys.stderr,
            )
            return 1
        print(f"Uploading {args.parquet} to {ITEM_ID}/{REMOTE_NAME}…")
        uploaded = publish_parquet(args.parquet, ia_key=ia_key, ia_secret=ia_secret)
        if not uploaded:
            print("  upload failed — proceeding to read-back for evidence anyway", file=sys.stderr)

    print("Reading back published artifact for verification…")
    proof = verify_published(args.parquet)

    evidence = build_evidence(parquet_path=args.parquet, uploaded=uploaded, proof=proof)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, ensure_ascii=False))

    if not evidence["published"]:
        print("FATAL: publication proof failed — not recording this as published", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
