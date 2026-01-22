#!/usr/bin/env python3
"""Export embeddings to Parquet for Internet Archive upload.

Creates compressed Parquet files optimized for archival storage.
"""

import argparse
from pathlib import Path

import structlog

from causaganha.v2.analysis.embedding_models import JINA_V4_1024
from causaganha.v2.storage.connection import get_connection
from causaganha.v2.storage.embedding_storage import EmbeddingStorage


logger = structlog.get_logger()


def main():
    """Export embeddings to Parquet."""
    parser = argparse.ArgumentParser(
        description="Export embeddings to Parquet",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output Parquet file path",
    )
    parser.add_argument(
        "--intimation-id",
        type=int,
        default=None,
        help="Optional: Export only this intimation ID",
    )

    args = parser.parse_args()

    logger.info(
        "export_started",
        output=args.output,
        intimation_id=args.intimation_id,
    )

    # Create storage
    storage = EmbeddingStorage(get_connection("data/causaganha.duckdb"))

    # Export to Parquet
    try:
        output_path = storage.export_to_parquet(
            output_path=args.output,
            model=JINA_V4_1024,
            intimation_id=args.intimation_id,
        )

        file_size_mb = output_path.stat().st_size / (1024 * 1024)

        logger.info(
            "export_completed",
            output=str(output_path),
            file_size_mb=round(file_size_mb, 2),
        )

        print(f"✅ Exported to: {output_path}")
        print(f"   Size: {file_size_mb:.2f} MB (ZSTD compressed)")

    except ValueError as e:
        logger.warning("export_failed", error=str(e))
        print(f"⚠️  No embeddings to export: {e}")
        # Create empty file to avoid workflow failure
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).touch()


if __name__ == "__main__":
    main()
