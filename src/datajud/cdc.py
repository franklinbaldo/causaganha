"""Change Data Capture (CDC) engine for bulk/incremental DataJud sync and IA backup.

Implements the delta-based ingestion pipeline outlined in Issue #1701:
- Uses `DataJudClient.iter_updated_since` (search_after cursor pagination).
- Checkpointing in SQLite (resilient, atomic state resumption per tribunal).
- Writes raw incoming batches as L1 deltas in partitioned Parquet files.
- Consolidates L1 deltas into canonical L0 Parquet tables with natural key deduplication.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyarrow.parquet as pq
import structlog
from pydantic import ValidationError

from datajud import archive
from datajud.client import DataJudClient
from datajud.daily_pack import (
    DEFAULT_DAILY_DIR,
    DEFAULT_INDEX_DIR,
    export_daily_locators,
    pack_daily_zip,
    update_resolution_index,
)
from datajud.dedup import capa_row_key, merge_capa_rows, merge_movimento_rows
from datajud.models import ProcessoCapa


if TYPE_CHECKING:
    from collections.abc import Sequence


log = structlog.get_logger()

DEFAULT_CDC_DIR = Path("data/datajud/cdc")
DEFAULT_CANONICAL_DIR = Path("data/datajud")


@dataclass
class CdcCheckpoint:
    """Persistent state of a CDC synchronization job for one tribunal."""

    tribunal: str
    since_iso: str | None = None
    until_iso: str | None = None
    last_sort_key: list[Any] | None = None
    last_updated_at: str | None = None
    total_documents: int = 0
    total_batches: int = 0
    last_run_at: str = ""
    status: str = "in_progress"  # "in_progress", "completed", "error"


class DataJudCdcCheckpointStore:
    """Thread-safe SQLite store for CDC resumption tokens."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS datajud_cdc_checkpoints (
                    tribunal TEXT PRIMARY KEY,
                    since_iso TEXT,
                    until_iso TEXT,
                    last_sort_key_json TEXT,
                    last_updated_at TEXT,
                    total_documents INTEGER NOT NULL DEFAULT 0,
                    total_batches INTEGER NOT NULL DEFAULT 0,
                    last_run_at TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                """
            )

    def get(self, tribunal: str) -> CdcCheckpoint | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM datajud_cdc_checkpoints WHERE tribunal = ?",
                (tribunal.lower(),),
            ).fetchone()
            if row is None:
                return None
            sort_key = (
                json.loads(row["last_sort_key_json"])
                if row["last_sort_key_json"] is not None
                else None
            )
            return CdcCheckpoint(
                tribunal=row["tribunal"],
                since_iso=row["since_iso"],
                until_iso=row["until_iso"],
                last_sort_key=sort_key,
                last_updated_at=row["last_updated_at"],
                total_documents=row["total_documents"],
                total_batches=row["total_batches"],
                last_run_at=row["last_run_at"],
                status=row["status"],
            )

    def upsert(self, cp: CdcCheckpoint) -> None:
        sort_key_json = (
            json.dumps(cp.last_sort_key) if cp.last_sort_key is not None else None
        )
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO datajud_cdc_checkpoints (
                    tribunal, since_iso, until_iso, last_sort_key_json,
                    last_updated_at, total_documents, total_batches,
                    last_run_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tribunal) DO UPDATE SET
                    since_iso = excluded.since_iso,
                    until_iso = excluded.until_iso,
                    last_sort_key_json = excluded.last_sort_key_json,
                    last_updated_at = excluded.last_updated_at,
                    total_documents = excluded.total_documents,
                    total_batches = excluded.total_batches,
                    last_run_at = excluded.last_run_at,
                    status = excluded.status;
                """,
                (
                    cp.tribunal.lower(),
                    cp.since_iso,
                    cp.until_iso,
                    sort_key_json,
                    cp.last_updated_at,
                    cp.total_documents,
                    cp.total_batches,
                    cp.last_run_at,
                    cp.status,
                ),
            )

    def reset(self, tribunal: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM datajud_cdc_checkpoints WHERE tribunal = ?",
                (tribunal.lower(),),
            )


def read_parquet_rows(path: Path) -> list[dict]:
    """Read a Parquet file into a list of row dicts (empty if file does not exist)."""
    if not path.exists():
        return []
    return pq.read_table(path).to_pylist()


def write_delta_batch(
    sources: Sequence[dict],
    tribunal: str,
    part_seq: int,
    deltas_dir: Path,
) -> tuple[Path | None, Path | None, int, int]:
    """Parse raw ES hits into capa + movimento rows and write delta Parquet files.

    Returns:
        (capa_path, mov_path, n_capas, n_movs)
    """
    consultado_em = datetime.now(UTC).isoformat(timespec="seconds")
    capas: list[ProcessoCapa] = []

    for src in sources:
        try:
            capas.append(ProcessoCapa.from_source(src))
        except ValidationError as exc:
            log.warning(
                "datajud_cdc_malformed_document",
                tribunal=tribunal,
                numeroProcesso=src.get("numeroProcesso"),
                error=str(exc),
            )

    if not capas:
        return None, None, 0, 0

    capa_rows = [
        c.capa_row(tribunal=tribunal, consultado_em=consultado_em) for c in capas
    ]
    mov_rows = [row for c in capas for row in c.movimento_rows(tribunal=tribunal)]

    tribunal_slug = tribunal.lower()
    tribunal_deltas_dir = deltas_dir / tribunal_slug
    tribunal_deltas_dir.mkdir(parents=True, exist_ok=True)

    capa_path = (
        tribunal_deltas_dir / f"capa_delta_{tribunal_slug}_{part_seq:06d}.parquet"
    )
    mov_path = tribunal_deltas_dir / f"mov_delta_{tribunal_slug}_{part_seq:06d}.parquet"

    n_capa = archive.write_capa_parquet(capa_rows, capa_path, tribunal=tribunal_slug)
    n_mov = archive.write_movimentos_parquet(mov_rows, mov_path, tribunal=tribunal_slug)

    return capa_path, mov_path, n_capa, n_mov


def compact_deltas(
    tribunal: str,
    *,
    deltas_dir: Path,
    canonical_dir: Path,
    clean_after_compact: bool = True,
) -> tuple[Path, Path, int, int]:
    """Merge all L1 delta Parquet files of *tribunal* into the canonical L0 Parquet tables.

    Uses :func:`merge_capa_rows` and :func:`merge_movimento_rows` for natural-key
    upserting, preserving the latest `dataHoraUltimaAtualizacao`.

    Returns:
        (canonical_capa_path, canonical_mov_path, total_capa_rows, total_mov_rows)
    """
    tribunal_slug = tribunal.lower()
    trib_deltas_dir = deltas_dir / tribunal_slug

    canonical_dir.mkdir(parents=True, exist_ok=True)
    capa_canonical = canonical_dir / archive.capa_parquet_name(tribunal_slug)
    mov_canonical = canonical_dir / archive.movimentos_parquet_name(tribunal_slug)

    existing_capas = read_parquet_rows(capa_canonical)
    existing_movs = read_parquet_rows(mov_canonical)

    if not trib_deltas_dir.exists():
        return capa_canonical, mov_canonical, len(existing_capas), len(existing_movs)

    capa_delta_files = sorted(trib_deltas_dir.glob("capa_delta_*.parquet"))
    mov_delta_files = sorted(trib_deltas_dir.glob("mov_delta_*.parquet"))

    if not capa_delta_files and not mov_delta_files:
        return capa_canonical, mov_canonical, len(existing_capas), len(existing_movs)

    # Apply delta batches sequentially so newer batches override older movements
    merged_capas = existing_capas
    merged_movs = existing_movs

    capa_by_seq: dict[str, Path] = {
        f.name.replace("capa_delta_", ""): f for f in capa_delta_files
    }
    mov_by_seq: dict[str, Path] = {
        f.name.replace("mov_delta_", ""): f for f in mov_delta_files
    }

    all_seqs = sorted(set(capa_by_seq.keys()) | set(mov_by_seq.keys()))
    for seq in all_seqs:
        batch_capas = read_parquet_rows(capa_by_seq[seq]) if seq in capa_by_seq else []
        batch_movs = read_parquet_rows(mov_by_seq[seq]) if seq in mov_by_seq else []
        refreshed_keys = {capa_row_key(r) for r in batch_capas}

        merged_capas = merge_capa_rows(merged_capas, batch_capas)
        merged_movs = merge_movimento_rows(merged_movs, batch_movs, refreshed_keys)

    n_capa = archive.write_capa_parquet(
        merged_capas, capa_canonical, tribunal=tribunal_slug
    )
    n_mov = archive.write_movimentos_parquet(
        merged_movs, mov_canonical, tribunal=tribunal_slug
    )

    if clean_after_compact:
        for f in [*capa_delta_files, *mov_delta_files]:
            try:
                f.unlink()
            except OSError as exc:
                log.warning("datajud_delta_cleanup_error", file=str(f), error=str(exc))

    log.info(
        "datajud_cdc_compacted",
        tribunal=tribunal_slug,
        delta_files=len(capa_delta_files),
        total_capas=n_capa,
        total_movs=n_mov,
    )
    return capa_canonical, mov_canonical, n_capa, n_mov


@dataclass
class CdcSyncResult:
    """Result summary of a CDC sync session."""

    tribunal: str
    documents_streamed: int
    batches_streamed: int
    checkpoint: CdcCheckpoint
    consolidated_capas: int | None = None
    consolidated_movs: int | None = None
    daily_zip_path: Path | None = None
    daily_processes_count: int = 0
    index_total: int = 0
    uploaded_files: list[str] | None = None


async def sync_tribunal_cdc(
    tribunal: str,
    *,
    since_iso: str | None = None,
    until_iso: str | None = None,
    page_size: int = 1000,
    min_page_size: int = 100,
    max_pages: int | None = None,
    pause_between_pages: float = 0.5,
    resume: bool = True,
    consolidate: bool = True,
    pack_daily: bool = True,
    upload: bool = False,
    base_dir: Path = DEFAULT_CDC_DIR,
    canonical_dir: Path = DEFAULT_CANONICAL_DIR,
    daily_dir: Path = DEFAULT_DAILY_DIR,
    index_dir: Path = DEFAULT_INDEX_DIR,
    ia_key: str = "",
    ia_secret: str = "",
    client: DataJudClient | None = None,
) -> CdcSyncResult:
    """Stream changed processes for a tribunal, writing L1 deltas and updating checkpoints.

    Args:
        tribunal: Sigla of the tribunal (e.g. "tjro").
        since_iso: Start cutoff ISO timestamp. If `resume` is True, previously saved
            checkpoint `last_sort_key` takes precedence.
        until_iso: Optional upper bound cutoff ISO timestamp.
        page_size: Initial Elasticsearch search_after page size.
        min_page_size: Minimum page size during adaptive backoff.
        max_pages: Optional maximum pages to pull before yielding.
        pause_between_pages: Sleep pause in seconds between page requests.
        resume: If True, resumes from SQLite checkpoint if available.
        consolidate: If True, automatically merges L1 deltas into canonical L0 Parquet tables.
        pack_daily: If True, packages all full processes in a daily ZIP for Internet Archive.
        upload: If True, uploads daily ZIP, index, and canonical Parquets to Internet Archive.
        base_dir: Directory for checkpoints SQLite and L1 deltas.
        canonical_dir: Directory for canonical L0 Parquet tables.
        daily_dir: Directory for daily ZIP archives.
        index_dir: Directory for resolution index Parquet table.
        ia_key: Internet Archive S3 access key.
        ia_secret: Internet Archive S3 secret key.
        client: Optional pre-configured `DataJudClient`.
    """
    tribunal_slug = tribunal.lower()
    store = DataJudCdcCheckpointStore(base_dir / "checkpoints.sqlite")
    deltas_dir = base_dir / "deltas"

    checkpoint = store.get(tribunal_slug) if resume else None
    if checkpoint is None:
        checkpoint = CdcCheckpoint(
            tribunal=tribunal_slug,
            since_iso=since_iso,
            until_iso=until_iso,
            last_run_at=datetime.now(UTC).isoformat(timespec="seconds"),
            status="in_progress",
        )
    else:
        checkpoint.status = "in_progress"
        checkpoint.last_run_at = datetime.now(UTC).isoformat(timespec="seconds")
        if since_iso and not checkpoint.since_iso:
            checkpoint.since_iso = since_iso
        if until_iso:
            checkpoint.until_iso = until_iso

    store.upsert(checkpoint)

    # Owns or uses injected client
    own_client = client is None
    active_client = client or DataJudClient(tribunal=tribunal_slug)

    try:
        if own_client:
            await active_client.__aenter__()

        part_seq = checkpoint.total_batches
        docs_session = 0
        batches_session = 0
        session_documents: list[dict[str, Any]] = []

        async for batch_hits, last_sort in active_client.iter_updated_since(
            since_iso=checkpoint.since_iso,
            until_iso=checkpoint.until_iso,
            page_size=page_size,
            min_page_size=min_page_size,
            max_pages=max_pages,
            pause_between_pages=pause_between_pages,
            search_after=checkpoint.last_sort_key,
        ):
            part_seq += 1
            batches_session += 1
            docs_session += len(batch_hits)
            session_documents.extend(batch_hits)

            # Write L1 Delta Parquet
            write_delta_batch(batch_hits, tribunal_slug, part_seq, deltas_dir)

            # Determine latest update timestamp in batch
            latest_update = max(
                (h.get("dataHoraUltimaAtualizacao") or "" for h in batch_hits),
                default="",
            )

            # Update checkpoint state atomically
            checkpoint.last_sort_key = last_sort
            if latest_update:
                checkpoint.last_updated_at = latest_update
            checkpoint.total_documents += len(batch_hits)
            checkpoint.total_batches = part_seq
            checkpoint.last_run_at = datetime.now(UTC).isoformat(timespec="seconds")
            store.upsert(checkpoint)

            log.info(
                "datajud_cdc_batch_saved",
                tribunal=tribunal_slug,
                batch_seq=part_seq,
                batch_size=len(batch_hits),
                total_documents=checkpoint.total_documents,
            )

        checkpoint.status = "completed"
        store.upsert(checkpoint)

    except Exception as exc:  # per-session bulkhead, see docs/adr/0011
        checkpoint.status = "error"
        store.upsert(checkpoint)
        log.exception("datajud_cdc_sync_failed", tribunal=tribunal_slug, error=str(exc))
        raise

    finally:
        if own_client:
            await active_client.__aexit__(None, None, None)

    # Consolidate L1 deltas into L0 canonical Parquet if requested
    n_capa, n_mov = None, None
    capa_canonical, mov_canonical = None, None
    if consolidate:
        capa_canonical, mov_canonical, n_capa, n_mov = compact_deltas(
            tribunal_slug,
            deltas_dir=deltas_dir,
            canonical_dir=canonical_dir,
        )

    # Pack full process documents in daily ZIP if requested
    daily_zip_path = None
    daily_count = 0
    index_total = 0
    if pack_daily and session_documents:
        target_date = datetime.now(UTC).strftime("%Y-%m-%d")
        daily_zip_path, daily_count = pack_daily_zip(
            session_documents,
            tribunal_slug,
            target_date=target_date,
            output_dir=daily_dir,
        )
        index_path = index_dir / f"indice_processos_{tribunal_slug}.parquet"
        index_total = update_resolution_index(
            index_path,
            session_documents,
            daily_zip_path.name,
            tribunal=tribunal_slug,
        )

    # Upload to Internet Archive if requested
    uploaded_files: list[str] = []
    if upload and ia_key and ia_secret:
        to_upload: list[Path] = []
        if daily_zip_path and daily_zip_path.exists():
            to_upload.append(daily_zip_path)
            # The sidecar is generated from actual ZIP members, never inferred
            # from the legacy one-row-per-CNJ DataJud resolution index.
            to_upload.append(export_daily_locators(daily_zip_path, tribunal_slug))
        index_file = index_dir / f"indice_processos_{tribunal_slug}.parquet"
        if index_file.exists():
            to_upload.append(index_file)
        if capa_canonical and capa_canonical.exists():
            to_upload.append(capa_canonical)
        if mov_canonical and mov_canonical.exists():
            to_upload.append(mov_canonical)

        for p in to_upload:
            ok = archive.upload_file(p, tribunal_slug, ia_key, ia_secret)
            if ok:
                uploaded_files.append(p.name)

    return CdcSyncResult(
        tribunal=tribunal_slug,
        documents_streamed=docs_session,
        batches_streamed=batches_session,
        checkpoint=checkpoint,
        consolidated_capas=n_capa,
        consolidated_movs=n_mov,
        daily_zip_path=daily_zip_path,
        daily_processes_count=daily_count,
        index_total=index_total,
        uploaded_files=uploaded_files if upload else None,
    )
