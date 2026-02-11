#!/usr/bin/env python3
"""Generate embeddings for DJEN decisions (IA Parquet-based).

This script generates vector embeddings for judicial decisions stored in
Internet Archive Parquet files. It reads textos.parquet, generates embeddings
via Jina API, and uploads embeddings.parquet back to IA.

Usage:
    # Generate embeddings for a specific date
    python scripts/pipeline/embed_v2.py --date 2026-02-10

    # Generate for all consolidated dates
    python scripts/pipeline/embed_v2.py --all

    # Limit number of texts per date
    python scripts/pipeline/embed_v2.py --date 2026-02-10 --max-texts 500

    # Set timeout
    python scripts/pipeline/embed_v2.py --all --timeout-minutes 50
"""

import argparse
import hashlib
import io
import os
import time
from pathlib import Path

import httpx
import polars as pl
import structlog

logger = structlog.get_logger()

# Embedding configuration
EMBEDDING_DIM = 768  # Jina embedding dimension
BATCH_SIZE = 100
IA_BASE_URL = "https://archive.org/download"


def get_embedding_client():
    """Get embedding client (Jina or Google)."""
    jina_key = os.environ.get("JINA_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")

    if jina_key:
        try:
            def embed_texts(texts: list[str]) -> list[list[float]]:
                with httpx.Client(timeout=60) as client:
                    response = client.post(
                        "https://api.jina.ai/v1/embeddings",
                        headers={"Authorization": f"Bearer {jina_key}"},
                        json={
                            "model": "jina-embeddings-v2-base-pt",
                            "input": texts,
                        },
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return [item["embedding"] for item in data["data"]]
                    logger.warning("jina_api_error", status=response.status_code)
                    return []

            return embed_texts
        except ImportError:
            pass

    if google_key:
        try:
            import google.generativeai as genai

            genai.configure(api_key=google_key)

            def embed_texts(texts: list[str]) -> list[list[float]]:
                result = genai.embed_content(
                    model="models/embedding-001",
                    content=texts,
                    task_type="retrieval_document",
                )
                return result["embedding"]

            return embed_texts
        except ImportError:
            pass

    return None


def fetch_consolidated_dates() -> list[str]:
    """Fetch list of consolidated dates from IA catalog."""
    catalog_url = f"{IA_BASE_URL}/causaganha-catalog/backfill-progress.json"

    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(catalog_url)
            if response.status_code == 200:
                data = response.json()
                return sorted(data.get("dates_consolidated", []))
            logger.warning("catalog_fetch_failed", status=response.status_code)
            return []
    except Exception as e:
        logger.warning("catalog_error", error=str(e))
        return []


def fetch_texts_from_ia(date: str) -> pl.DataFrame | None:
    """Download textos.parquet from IA for a date."""
    item_name = f"djen-{date}"
    url = f"{IA_BASE_URL}/{item_name}/textos.parquet"

    try:
        logger.info("downloading_texts", date=date, url=url)
        with httpx.Client(timeout=120) as client:
            response = client.get(url)
            if response.status_code == 200:
                df = pl.read_parquet(io.BytesIO(response.content))
                logger.info("texts_downloaded", date=date, rows=len(df))
                return df
            logger.warning("texts_not_found", date=date, status=response.status_code)
            return None
    except Exception as e:
        logger.warning("texts_download_failed", date=date, error=str(e))
        return None


def fetch_existing_embeddings(date: str) -> set[str]:
    """Check which texts already have embeddings on IA."""
    item_name = f"djen-{date}"
    url = f"{IA_BASE_URL}/{item_name}/embeddings.parquet"

    try:
        logger.info("checking_existing_embeddings", date=date)
        with httpx.Client(timeout=60) as client:
            response = client.get(url)
            if response.status_code == 200:
                df = pl.read_parquet(io.BytesIO(response.content))
                existing = set(df["id"].to_list())
                logger.info("existing_embeddings_found", date=date, count=len(existing))
                return existing
            logger.info("no_existing_embeddings", date=date)
            return set()
    except Exception as e:
        logger.info("embeddings_check_failed", date=date, error=str(e))
        return set()


def _compute_md5(data: bytes) -> str:
    """Compute MD5 hash of data."""
    return hashlib.md5(data).hexdigest()


def upload_embeddings_to_ia(date: str, embeddings_df: pl.DataFrame) -> bool:
    """Upload embeddings.parquet to IA."""
    item_name = f"djen-{date}"
    filename = "embeddings.parquet"

    # Convert to parquet bytes
    buffer = io.BytesIO()
    embeddings_df.write_parquet(buffer)
    parquet_bytes = buffer.getvalue()
    md5_hash = _compute_md5(parquet_bytes)

    # Get access/secret from env
    access_key = os.environ.get("IA_ACCESS_KEY")
    secret_key = os.environ.get("IA_SECRET_KEY")

    if not access_key or not secret_key:
        logger.error("missing_ia_credentials")
        return False

    url = f"https://s3.us.archive.org/{item_name}/{filename}"
    headers = {
        "Authorization": f"LOW {access_key}:{secret_key}",
        "x-archive-auto-make-bucket": "1",
        "x-amz-auto-make-bucket": "1",
        "x-archive-meta-mediatype": "data",
        "Content-MD5": md5_hash,
    }

    try:
        logger.info("uploading_embeddings", date=date, size_mb=len(parquet_bytes) / 1024 / 1024)
        with httpx.Client(timeout=300) as client:
            for attempt in range(3):
                response = client.put(url, content=parquet_bytes, headers=headers)
                if response.status_code in (200, 201):
                    logger.info("embeddings_uploaded", date=date, attempt=attempt + 1)
                    return True
                logger.warning(
                    "upload_retry",
                    date=date,
                    attempt=attempt + 1,
                    status=response.status_code,
                )
                time.sleep(5)
            logger.error("upload_failed", date=date)
            return False
    except Exception as e:
        logger.error("upload_exception", date=date, error=str(e))
        return False


def generate_embeddings_for_date(
    date: str,
    max_texts: int = 500,
    embed_fn=None,
) -> dict:
    """Generate embeddings for a single date."""
    stats = {"processed": 0, "failed": 0, "uploaded": 0}

    # Fetch texts
    texts_df = fetch_texts_from_ia(date)
    if texts_df is None or len(texts_df) == 0:
        logger.info("no_texts_for_date", date=date)
        return stats

    # Fetch existing embeddings
    existing_ids = fetch_existing_embeddings(date)

    # Filter unprocessed texts
    if existing_ids:
        texts_df = texts_df.filter(~pl.col("id").is_in(existing_ids))

    if len(texts_df) == 0:
        logger.info("all_texts_already_embedded", date=date)
        return stats

    # Limit if requested
    if max_texts and len(texts_df) > max_texts:
        texts_df = texts_df.head(max_texts)

    logger.info("texts_to_embed", date=date, count=len(texts_df))

    # Filter valid texts (must have texto, length > 50)
    texts_df = texts_df.filter(
        (pl.col("texto").is_not_null()) & (pl.col("texto").str.len_chars() > 50)
    )

    if len(texts_df) == 0:
        logger.info("no_valid_texts", date=date)
        return stats

    # Generate embeddings in batches
    embeddings_data = []

    for i in range(0, len(texts_df), BATCH_SIZE):
        batch_df = texts_df[i : i + BATCH_SIZE]
        texts = [t[:8000] for t in batch_df["texto"].to_list()]  # Limit text length

        try:
            embeddings = embed_fn(texts)

            if embeddings and len(embeddings) == len(batch_df):
                for j, row in enumerate(batch_df.iter_rows(named=True)):
                    embeddings_data.append(
                        {
                            "id": row["id"],
                            "embedding": embeddings[j],
                        }
                    )
                stats["processed"] += len(batch_df)
                logger.info(
                    "batch_embedded",
                    date=date,
                    batch=i // BATCH_SIZE + 1,
                    count=len(batch_df),
                )
            else:
                stats["failed"] += len(batch_df)

        except Exception as e:
            logger.warning("batch_failed", date=date, error=str(e))
            stats["failed"] += len(batch_df)

        # Rate limiting
        time.sleep(0.5)

    if not embeddings_data:
        logger.warning("no_embeddings_generated", date=date)
        return stats

    # Create embeddings DataFrame
    embeddings_df = pl.DataFrame(embeddings_data)

    # Upload to IA
    if upload_embeddings_to_ia(date, embeddings_df):
        stats["uploaded"] = len(embeddings_df)
    else:
        logger.error("upload_failed", date=date)

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Generate embeddings for DJEN decisions (IA-based)"
    )
    parser.add_argument("--date", help="Specific date to process (YYYY-MM-DD)")
    parser.add_argument(
        "--all", action="store_true", help="Process all consolidated dates"
    )
    parser.add_argument("--max-texts", type=int, help="Max texts per date")
    parser.add_argument("--timeout-minutes", type=int, default=50)
    args = parser.parse_args()

    # Get embedding client
    embed_fn = get_embedding_client()
    if embed_fn is None:
        logger.error("no_embedding_client", hint="Set JINA_API_KEY or GOOGLE_API_KEY")
        print("ERROR: No embedding API key configured")
        print("Set JINA_API_KEY or GOOGLE_API_KEY environment variable")
        return 1

    # Get dates to process
    if args.date:
        dates = [args.date]
    elif args.all:
        dates = fetch_consolidated_dates()
        if not dates:
            print("No consolidated dates found in catalog")
            return 1
    else:
        print("ERROR: Specify --date or --all")
        return 1

    print(f"Processing {len(dates)} date(s)...")
    print()

    start_time = time.time()
    timeout_seconds = args.timeout_minutes * 60

    total_stats = {"processed": 0, "failed": 0, "uploaded": 0}

    for date in dates:
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logger.info("timeout_reached")
            break

        print(f"\n{'=' * 60}")
        print(f"Processing {date}")
        print('=' * 60)

        stats = generate_embeddings_for_date(
            date=date,
            max_texts=args.max_texts,
            embed_fn=embed_fn,
        )

        total_stats["processed"] += stats["processed"]
        total_stats["failed"] += stats["failed"]
        total_stats["uploaded"] += stats["uploaded"]

        print(f"  Processed: {stats['processed']}")
        print(f"  Failed:    {stats['failed']}")
        print(f"  Uploaded:  {stats['uploaded']}")

    print()
    print("=" * 60)
    print("EMBEDDING SUMMARY")
    print("=" * 60)
    print(f"  Dates:     {len(dates)}")
    print(f"  Processed: {total_stats['processed']}")
    print(f"  Failed:    {total_stats['failed']}")
    print(f"  Uploaded:  {total_stats['uploaded']}")

    # Output for GitHub Actions
    files_added = total_stats["uploaded"] > 0
    print(f"\n  Files added: {files_added}")

    if os_env := os.getenv("GITHUB_OUTPUT"):
        with open(os_env, "a") as f:
            f.write(f"files_added={'true' if files_added else 'false'}\n")
            f.write(f"embed_processed={total_stats['processed']}\n")
            f.write(f"embed_uploaded={total_stats['uploaded']}\n")
            f.write(f"embed_failed={total_stats['failed']}\n")

    return 0


if __name__ == "__main__":
    exit(main())
