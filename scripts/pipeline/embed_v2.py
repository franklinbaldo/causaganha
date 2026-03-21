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
import os
import sys
import tempfile
import time

import httpx
import ibis
import structlog


logger = structlog.get_logger()

# Embedding configuration
BATCH_SIZE = 100
IA_BASE_URL = "https://archive.org/download"


def get_embedding_client():
    """Get embedding client (Jina or Google)."""
    jina_key = os.environ.get("JINA_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")

    if jina_key:

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

            func = embed_texts
        except ImportError:
            pass
        else:
            return func

    return None


def _download_parquet(url: str, timeout: int = 120) -> str | None:
    """Download a parquet file from URL, return temp file path or None."""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            if response.status_code == 200:
                tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
                tmp.write(response.content)
                tmp.close()
                return tmp.name
            return None
    except Exception:
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


def fetch_texts_from_ia(con: ibis.BaseBackend, date: str, tribunal: str) -> ibis.Table | None:
    """Download textos.parquet from IA and register as ibis table."""
    year = date[:4]
    item_name = f"djen-{tribunal.lower()}-{year}"
    filename = f"{tribunal.upper()}-{date}-textos.parquet"
    url = f"{IA_BASE_URL}/{item_name}/{filename}"

    logger.info("downloading_texts", date=date, tribunal=tribunal, url=url)
    path = _download_parquet(url)
    if path is None:
        logger.warning("texts_not_found", date=date, tribunal=tribunal)
        return None

    try:
        t = con.read_parquet(path)
        row_count = t.count().execute()
        logger.info("texts_downloaded", date=date, tribunal=tribunal, rows=row_count)
        if row_count == 0:
            return None
        result = t
    except Exception as e:
        logger.warning("texts_download_failed", date=date, tribunal=tribunal, error=str(e))
        return None
    else:
        return result
    finally:
        os.unlink(path)


def fetch_existing_embedding_ids(con: ibis.BaseBackend, date: str, tribunal: str) -> set[str]:
    """Check which texts already have embeddings on IA."""
    year = date[:4]
    item_name = f"djen-{tribunal.lower()}-{year}"
    filename = f"{tribunal.upper()}-{date}-embeddings.parquet"
    url = f"{IA_BASE_URL}/{item_name}/{filename}"

    logger.info("checking_existing_embeddings", date=date, tribunal=tribunal)
    path = _download_parquet(url, timeout=60)
    if path is None:
        logger.info("no_existing_embeddings", date=date, tribunal=tribunal)
        return set()

    try:
        t = con.read_parquet(path)
        ids = t.select("id").to_pyarrow().column("id").to_pylist()
        logger.info("existing_embeddings_found", date=date, tribunal=tribunal, count=len(ids))
        return set(ids)
    except Exception as e:
        logger.info("embeddings_check_failed", date=date, tribunal=tribunal, error=str(e))
        return set()
    finally:
        os.unlink(path)


def _compute_md5(data: bytes) -> str:
    """Compute MD5 hash of data."""
    return hashlib.md5(data).hexdigest()


def upload_embeddings_to_ia(
    con: ibis.BaseBackend, date: str, tribunal: str, table_name: str
) -> bool:
    """Export embeddings table to parquet bytes and upload to IA."""
    year = date[:4]
    item_name = f"djen-{tribunal.lower()}-{year}"
    filename = f"{tribunal.upper()}-{date}-embeddings.parquet"

    # Export to parquet bytes via temp file
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        con.raw_sql(
            f"COPY {table_name} TO '{tmp_path}' (FORMAT PARQUET, COMPRESSION ZSTD)",
        )
        with open(tmp_path, "rb") as f:
            parquet_bytes = f.read()
    finally:
        os.unlink(tmp_path)

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
        logger.exception("upload_exception", date=date, error=str(e))
        return False


def generate_embeddings_for_date(
    date: str,
    tribunals: list[str],
    max_texts: int = 500,
    embed_fn=None,
) -> dict:
    """Generate embeddings for a single date across multiple tribunals."""
    stats = {"processed": 0, "failed": 0, "uploaded": 0}

    con = ibis.duckdb.connect()

    for tribunal in tribunals:
        logger.info("processing_tribunal", date=date, tribunal=tribunal)
        # Fetch texts
        texts = fetch_texts_from_ia(con, date, tribunal)
        if texts is None:
            logger.info("no_texts_for_date_tribunal", date=date, tribunal=tribunal)
            continue

        # Fetch existing embeddings
        existing_ids = fetch_existing_embedding_ids(con, date, tribunal)

        # Filter unprocessed texts using ibis
        if existing_ids:
            texts = texts.filter(~texts.id.isin(existing_ids))

        # Filter valid texts (must have texto, length > 50)
        texts = texts.filter(texts.texto.notnull() & (texts.texto.length() > 50))

        row_count = texts.count().execute()
        if row_count == 0:
            logger.info("all_texts_already_embedded", date=date, tribunal=tribunal)
            continue

        # Limit if requested
        if max_texts and row_count > max_texts:
            texts = texts.limit(max_texts)
            row_count = max_texts

        logger.info("texts_to_embed", date=date, tribunal=tribunal, count=row_count)

        # Stream batches directly from ibis for API calls
        result_ids = []
        result_embeddings = []
        batch_num = 0

        for batch in texts.select("id", "texto").to_pyarrow_batches(chunk_size=BATCH_SIZE):
            batch_num += 1
            batch_texts = [t[:8000] for t in batch.column("texto").to_pylist()]

            try:
                embeddings = embed_fn(batch_texts)

                if embeddings and len(embeddings) == len(batch):
                    result_ids.extend(batch.column("id").to_pylist())
                    result_embeddings.extend(embeddings)
                    stats["processed"] += len(batch)
                    logger.info(
                        "batch_embedded",
                        date=date,
                        tribunal=tribunal,
                        batch=batch_num,
                        count=len(batch),
                    )
                else:
                    stats["failed"] += len(batch)

            except Exception as e:
                logger.warning("batch_failed", date=date, tribunal=tribunal, error=str(e))
                stats["failed"] += len(batch)

            # Rate limiting
            time.sleep(0.5)

        if not result_ids:
            logger.warning("no_embeddings_generated", date=date, tribunal=tribunal)
            continue

        # Register results as ibis table for export
        emb_table_name = f"embeddings_out_{tribunal.lower()}"
        con.raw_sql(f"DROP TABLE IF EXISTS {emb_table_name}")
        con.create_table(
            emb_table_name,
            ibis.memtable({"id": result_ids, "embedding": result_embeddings}),
        )

        # Upload to IA
        if upload_embeddings_to_ia(con, date, tribunal, emb_table_name):
            stats["uploaded"] += len(result_ids)
        else:
            logger.error("upload_failed", date=date, tribunal=tribunal)

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate embeddings for DJEN decisions (IA-based)"
    )
    parser.add_argument("--date", help="Specific date to process (YYYY-MM-DD)")
    parser.add_argument("--all", action="store_true", help="Process all consolidated dates")
    parser.add_argument("--max-texts", type=int, help="Max texts per date")
    parser.add_argument("--timeout-minutes", type=int, default=50)
    args = parser.parse_args()

    # Get embedding client
    embed_fn = get_embedding_client()
    if embed_fn is None:
        logger.error("no_embedding_client", hint="Set JINA_API_KEY or GOOGLE_API_KEY")
        return 1

    # Get dates to process
    if args.date:
        dates = [args.date]
    elif args.all:
        dates = fetch_consolidated_dates()
        if not dates:
            return 1
    else:
        return 1

    start_time = time.time()
    timeout_seconds = args.timeout_minutes * 60

    total_stats = {"processed": 0, "failed": 0, "uploaded": 0}

    for date in dates:
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logger.info("timeout_reached")
            break

        from causaganha.config import TRIBUNAIS

        stats = generate_embeddings_for_date(
            date=date,
            tribunals=TRIBUNAIS,
            max_texts=args.max_texts,
            embed_fn=embed_fn,
        )

        total_stats["processed"] += stats["processed"]
        total_stats["failed"] += stats["failed"]
        total_stats["uploaded"] += stats["uploaded"]

    # Output for GitHub Actions
    files_added = total_stats["uploaded"] > 0

    if os_env := os.getenv("GITHUB_OUTPUT"):
        with open(os_env, "a") as f:
            f.write(f"files_added={'true' if files_added else 'false'}\n")
            f.write(f"embed_processed={total_stats['processed']}\n")
            f.write(f"embed_uploaded={total_stats['uploaded']}\n")
            f.write(f"embed_failed={total_stats['failed']}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
