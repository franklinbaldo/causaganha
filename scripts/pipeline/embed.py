#!/usr/bin/env python3
"""Generate embeddings for DJEN decisions.

Reads unembedded decisions from a local DuckDB, calls an embedding API
(Jina or Google), and writes the vectors back. Designed to run as a
pipeline step from run.py.

Usage:
    python scripts/pipeline/embed.py --max-decisions 100
    python scripts/pipeline/embed.py --deadline 10m
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import structlog
from causaganha.storage.connection import get_connection


if TYPE_CHECKING:
    from collections.abc import Callable

logger = structlog.get_logger()

EMBEDDING_DIM = 768
BATCH_SIZE = 100
MAX_TEXT_LENGTH = 8000


# ── Embedding providers ──────────────────────────────────────


def _jina_embed(api_key: str) -> Callable[[list[str]], list[list[float]]]:
    import httpx

    def embed(texts: list[str]) -> list[list[float]]:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                "https://api.jina.ai/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "jina-embeddings-v2-base-pt", "input": texts},
            )
            resp.raise_for_status()
            return [item["embedding"] for item in resp.json()["data"]]

    return embed


def _google_embed(api_key: str) -> Callable[[list[str]], list[list[float]]]:
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    def embed(texts: list[str]) -> list[list[float]]:
        result = genai.embed_content(
            model="models/embedding-001",
            content=texts,
            task_type="retrieval_document",
        )
        return result["embedding"]

    return embed


def get_embed_fn() -> Callable[[list[str]], list[list[float]]] | None:
    """Return an embedding function based on available API keys."""
    if key := os.environ.get("JINA_API_KEY"):
        return _jina_embed(key)
    if key := os.environ.get("GOOGLE_API_KEY"):
        return _google_embed(key)
    return None


# ── Database ─────────────────────────────────────────────────


def fetch_unembedded(db_path: Path, limit: int) -> list[tuple[str, str]]:
    """Return (id, texto) pairs for decisions missing embeddings."""
    if not db_path.exists():
        return []

    # Use singleton connection
    backend = get_connection(str(db_path), read_only=True)
    con = backend.con
    try:
        tables = {t[0] for t in con.execute("SHOW TABLES").fetchall()}
        if "decisions" not in tables:
            return []

        has_embeddings = "embeddings" in tables
        query = """
            SELECT d.id, d.texto
            FROM decisions d
            {join}
            WHERE {filter} d.texto IS NOT NULL AND LENGTH(d.texto) > 50
            LIMIT ?
        """.format(
            join="LEFT JOIN embeddings e ON d.id = e.decision_id" if has_embeddings else "",
            filter="e.decision_id IS NULL AND" if has_embeddings else "",
        )
        return con.execute(query, [limit]).fetchall()
    except duckdb.Error as e:
        logger.warning("query_failed", error=str(e))
        return []


def save_embeddings(db_path: Path, rows: list[tuple[str, list[float]]]) -> int:
    """Batch-insert (decision_id, embedding) rows. Returns count saved."""
    if not rows:
        return 0

    # Use singleton connection (read-write)
    backend = get_connection(str(db_path), read_only=False)
    con = backend.con

    con.execute(f"""
        CREATE TABLE IF NOT EXISTS embeddings (
            decision_id VARCHAR PRIMARY KEY,
            embedding FLOAT[{EMBEDDING_DIM}],
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.executemany(
        "INSERT OR REPLACE INTO embeddings (decision_id, embedding) VALUES (?, ?)",
        rows,
    )
    return len(rows)


# ── Main loop ────────────────────────────────────────────────


def generate_embeddings(
    *,
    embed_fn: Callable[[list[str]], list[list[float]]],
    db_path: Path,
    max_decisions: int,
    deadline_seconds: float,
) -> dict[str, int]:
    """Fetch, embed, and save decisions in batches until done or deadline."""
    stats: dict[str, int] = {"processed": 0, "saved": 0, "failed": 0}
    start = time.monotonic()

    decisions = fetch_unembedded(db_path, limit=max_decisions)
    if not decisions:
        logger.info("no_decisions_to_embed")
        return stats

    logger.info("decisions_to_embed", count=len(decisions))

    for i in range(0, len(decisions), BATCH_SIZE):
        if time.monotonic() - start > deadline_seconds:
            logger.info("deadline_reached")
            break

        batch = decisions[i : i + BATCH_SIZE]
        texts = [texto[:MAX_TEXT_LENGTH] for _, texto in batch]

        try:
            vectors = embed_fn(texts)
            if len(vectors) != len(batch):
                stats["failed"] += len(batch)
                continue

            rows = [(did, vec) for (did, _), vec in zip(batch, vectors, strict=True)]
            saved = save_embeddings(db_path, rows)
            stats["saved"] += saved
            stats["processed"] += len(batch)
            logger.info("batch_saved", batch=i // BATCH_SIZE + 1, saved=saved)

        except Exception as e:
            logger.warning("batch_failed", error=str(e))
            stats["failed"] += len(batch)

        time.sleep(0.5)

    return stats


# ── CLI ──────────────────────────────────────────────────────


def _parse_deadline(s: str) -> float:
    """Parse '10m' or '600s' to seconds."""
    if s.endswith("m"):
        return float(s[:-1]) * 60
    if s.endswith("s"):
        return float(s[:-1])
    return float(s)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate embeddings for DJEN decisions")
    parser.add_argument("--max-decisions", type=int, default=500)
    parser.add_argument("--deadline", default="10m", help="e.g. 10m, 600s")
    parser.add_argument("--db-path", default="data/embeddings.duckdb")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    deadline_seconds = _parse_deadline(args.deadline)

    embed_fn = get_embed_fn()
    if embed_fn is None:
        print("ERROR: Set JINA_API_KEY or GOOGLE_API_KEY")
        return 0  # not a pipeline failure, just nothing to do

    stats = generate_embeddings(
        embed_fn=embed_fn,
        db_path=db_path,
        max_decisions=args.max_decisions,
        deadline_seconds=deadline_seconds,
    )

    print(
        f"\nEmbedding: processed={stats['processed']} saved={stats['saved']} failed={stats['failed']}"
    )

    if gh_output := os.getenv("GITHUB_OUTPUT"):
        with Path(gh_output).open("a") as f:
            f.write(f"files_added={'true' if stats['saved'] > 0 else 'false'}\n")
            f.write(f"embed_processed={stats['processed']}\n")
            f.write(f"embed_saved={stats['saved']}\n")
            f.write(f"embed_failed={stats['failed']}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
