#!/usr/bin/env python3
"""Generate embeddings for DJEN decisions.

This script generates vector embeddings for judicial decisions to enable
semantic search. It reads decisions from Parquet files on Internet Archive
and stores embeddings in a local DuckDB database.

Usage:
    # Generate embeddings for unprocessed decisions
    python scripts/pipeline/embed.py

    # Limit number of decisions
    python scripts/pipeline/embed.py --max-decisions 100

    # Set timeout
    python scripts/pipeline/embed.py --timeout-minutes 50
"""

import argparse
import os
import time
from pathlib import Path

import structlog


logger = structlog.get_logger()

# Embedding configuration
EMBEDDING_DIM = 768  # Jina embedding dimension
BATCH_SIZE = 100


def get_embedding_client():
    """Get embedding client (Jina or Google)."""
    jina_key = os.environ.get("JINA_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")

    if jina_key:
        try:
            import httpx

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


def get_unembedded_decisions(db_path: Path, limit: int = 500) -> list[dict]:
    """Get decisions that haven't been embedded yet."""
    import duckdb

    if not db_path.exists():
        return []

    con = duckdb.connect(str(db_path), read_only=True)

    try:
        # Check if tables exist
        tables = con.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]

        if "decisions" not in table_names:
            return []

        if "embeddings" in table_names:
            query = """
                SELECT d.id, d.texto
                FROM decisions d
                LEFT JOIN embeddings e ON d.id = e.decision_id
                WHERE e.decision_id IS NULL
                AND d.texto IS NOT NULL
                AND LENGTH(d.texto) > 50
                LIMIT ?
            """
        else:
            query = """
                SELECT id, texto
                FROM decisions
                WHERE texto IS NOT NULL
                AND LENGTH(texto) > 50
                LIMIT ?
            """

        results = con.execute(query, [limit]).fetchall()
        return [{"id": r[0], "texto": r[1]} for r in results]

    except Exception as e:
        logger.warning("query_failed", error=str(e))
        return []
    finally:
        con.close()


def save_embeddings(db_path: Path, embeddings: list[dict]) -> int:
    """Save embeddings to DuckDB."""
    import duckdb

    if not embeddings:
        return 0

    con = duckdb.connect(str(db_path))

    try:
        # Create embeddings table if not exists
        con.execute(f"""
            CREATE TABLE IF NOT EXISTS embeddings (
                decision_id VARCHAR PRIMARY KEY,
                embedding FLOAT[{EMBEDDING_DIM}],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert embeddings
        saved = 0
        for emb in embeddings:
            try:
                con.execute(
                    "INSERT OR REPLACE INTO embeddings (decision_id, embedding) VALUES (?, ?)",
                    [emb["id"], emb["embedding"]],
                )
                saved += 1
            except Exception:
                continue

        return saved

    finally:
        con.close()


def generate_embeddings(
    max_decisions: int = 500,
    timeout_minutes: int = 50,
    db_path: Path = Path("data/embeddings.duckdb"),
) -> dict:
    """Main embedding generation function."""
    stats = {"processed": 0, "failed": 0, "saved": 0}

    # Get embedding client
    embed_fn = get_embedding_client()
    if embed_fn is None:
        logger.error("no_embedding_client", hint="Set JINA_API_KEY or GOOGLE_API_KEY")
        print("ERROR: No embedding API key configured")
        print("Set JINA_API_KEY or GOOGLE_API_KEY environment variable")
        return stats

    # Get unembedded decisions
    decisions = get_unembedded_decisions(db_path, limit=max_decisions)
    if not decisions:
        logger.info("no_decisions_to_embed")
        return stats

    logger.info("decisions_to_embed", count=len(decisions))

    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    # Process in batches
    for i in range(0, len(decisions), BATCH_SIZE):
        # Check timeout
        if time.time() - start_time > timeout_seconds:
            logger.info("timeout_reached")
            break

        batch = decisions[i : i + BATCH_SIZE]
        texts = [d["texto"][:8000] for d in batch]  # Limit text length

        try:
            embeddings = embed_fn(texts)

            if embeddings and len(embeddings) == len(batch):
                to_save = [
                    {"id": batch[j]["id"], "embedding": embeddings[j]} for j in range(len(batch))
                ]
                saved = save_embeddings(db_path, to_save)
                stats["saved"] += saved
                stats["processed"] += len(batch)
                logger.info("batch_processed", batch=i // BATCH_SIZE + 1, saved=saved)
            else:
                stats["failed"] += len(batch)

        except Exception as e:
            logger.warning("batch_failed", error=str(e))
            stats["failed"] += len(batch)

        # Rate limiting
        time.sleep(0.5)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for DJEN decisions")
    parser.add_argument("--max-decisions", type=int, default=500)
    parser.add_argument("--timeout-minutes", type=int, default=50)
    parser.add_argument(
        "--deadline", help="Exit after this duration (e.g., 10m, 600s)", default="10m"
    )
    parser.add_argument("--db-path", default="data/embeddings.duckdb")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    print("Generating embeddings...")
    print(f"  Max decisions: {args.max_decisions}")
    print(f"  Timeout: {args.timeout_minutes} minutes")
    print(f"  Database: {db_path}")
    print()

    stats = generate_embeddings(
        max_decisions=args.max_decisions,
        timeout_minutes=args.timeout_minutes,
        db_path=db_path,
    )

    print()
    print("=" * 40)
    print("EMBEDDING SUMMARY")
    print("=" * 40)
    print(f"  Processed: {stats['processed']}")
    print(f"  Saved:     {stats['saved']}")
    print(f"  Failed:    {stats['failed']}")

    # Set GitHub Actions output: did we add any files?
    files_added = stats["saved"] > 0
    print(f"\n  Files added: {files_added}")

    # Output for GitHub Actions conditional triggers
    if os_env := os.getenv("GITHUB_OUTPUT"):
        with open(os_env, "a") as f:
            f.write(f"files_added={'true' if files_added else 'false'}\n")

    return 0


if __name__ == "__main__":
    exit(main())
