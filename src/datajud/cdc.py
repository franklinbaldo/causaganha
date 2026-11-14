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
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pyarrow.parquet as pq
import structlog
from pydantic import ValidationError

from datajud import archive, cdc_state
from datajud.client import DataJudClient
from datajud.daily_pack import (
    DEFAULT_DAILY_DIR,
    DEFAULT_INDEX_DIR,
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
    # "in_progress" while streaming; "collected" once the stream stopped and the
    # local artifacts were built; "published" only after every artifact and the
    # commit bundle reached Internet Archive; "error" on any failure.
    status: str = "in_progress"


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
        sort_key_json = json.dumps(cp.last_sort_key) if cp.last_sort_key is not None else None
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

    capa_rows = [c.capa_row(tribunal=tribunal, consultado_em=consultado_em) for c in capas]
    mov_rows = [row for c in capas for row in c.movimento_rows(tribunal=tribunal)]

    tribunal_slug = tribunal.lower()
    tribunal_deltas_dir = deltas_dir / tribunal_slug
    tribunal_deltas_dir.mkdir(parents=True, exist_ok=True)

    capa_path = tribunal_deltas_dir / f"capa_delta_{tribunal_slug}_{part_seq:06d}.parquet"
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

    capa_by_seq: dict[str, Path] = {f.name.replace("capa_delta_", ""): f for f in capa_delta_files}
    mov_by_seq: dict[str, Path] = {f.name.replace("mov_delta_", ""): f for f in mov_delta_files}

    all_seqs = sorted(set(capa_by_seq.keys()) | set(mov_by_seq.keys()))
    for seq in all_seqs:
        batch_capas = read_parquet_rows(capa_by_seq[seq]) if seq in capa_by_seq else []
        batch_movs = read_parquet_rows(mov_by_seq[seq]) if seq in mov_by_seq else []
        refreshed_keys = {capa_row_key(r) for r in batch_capas}

        merged_capas = merge_capa_rows(merged_capas, batch_capas)
        merged_movs = merge_movimento_rows(merged_movs, batch_movs, refreshed_keys)

    n_capa = archive.write_capa_parquet(merged_capas, capa_canonical, tribunal=tribunal_slug)
    n_mov = archive.write_movimentos_parquet(merged_movs, mov_canonical, tribunal=tribunal_slug)

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
    stream_exhausted: bool = False
    restore_status: str | None = None


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
    restore_remote: bool = False,
    max_duration_s: float | None = None,
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
        restore_remote: Restore the last published CDC generation (checkpoint,
            canonical Parquets, index) from Internet Archive before streaming.
            Required on ephemeral runners; fails closed on anything but a 404.
        max_duration_s: Stop streaming after this many seconds so the run can
            still consolidate and publish before the runner times out. The
            cursor then resumes on the next run.

    Raises:
        cdc_state.CdcStateError: upload requested without credentials, remote
            state unreadable, or any artifact failed to publish. The commit
            bundle is published last, so a failure never advances the cursor
            that the next runner restores.
    """
    tribunal_slug = tribunal.lower()
    if upload and not (ia_key and ia_secret):
        msg = "upload requested but Internet Archive credentials are missing"
        raise cdc_state.CdcStateError(msg)

    store = DataJudCdcCheckpointStore(base_dir / "checkpoints.sqlite")
    deltas_dir = base_dir / "deltas"

    restore_status: str | None = None
    if restore_remote:
        restored = cdc_state.restore_cdc_state(
            tribunal_slug, canonical_dir=canonical_dir, index_dir=index_dir
        )
        restore_status = restored.status
        log.info(
            "datajud_cdc_state_restored",
            tribunal=tribunal_slug,
            status=restored.status,
            generation=restored.generation,
        )
        if resume and restored.checkpoint is not None:
            store.upsert(CdcCheckpoint(**restored.checkpoint))

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
        started = time.monotonic()
        stream_exhausted = True

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

            if max_duration_s is not None and time.monotonic() - started >= max_duration_s:
                stream_exhausted = False
                log.info(
                    "datajud_cdc_time_budget_reached",
                    tribunal=tribunal_slug,
                    elapsed_s=round(time.monotonic() - started),
                    total_documents=checkpoint.total_documents,
                )
                break

        checkpoint.status = "collected"
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
        # Run-unique name: a second run on the same day must not overwrite the
        # first day's snapshot that the published index may still point to
        # (issue #1707).
        target_date = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
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

    uploaded_files: list[str] = []
    if upload:
        try:
            uploaded_files = _publish(
                tribunal_slug,
                checkpoint=checkpoint,
                daily_zip_path=daily_zip_path,
                capa_canonical=capa_canonical,
                mov_canonical=mov_canonical,
                index_file=index_dir / cdc_state.index_name(tribunal_slug),
                ia_key=ia_key,
                ia_secret=ia_secret,
            )
        except cdc_state.CdcStateError:
            checkpoint.status = "error"
            store.upsert(checkpoint)
            raise
        store.upsert(checkpoint)

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
        stream_exhausted=stream_exhausted,
        restore_status=restore_status,
    )


def _upload_or_raise(path: Path, tribunal: str, ia_key: str, ia_secret: str) -> None:
    if not archive.upload_file(path, tribunal, ia_key, ia_secret):
        msg = f"failed to publish {path.name} to Internet Archive"
        raise cdc_state.CdcStateError(msg)


def _publish(
    tribunal: str,
    *,
    checkpoint: CdcCheckpoint,
    daily_zip_path: Path | None,
    capa_canonical: Path | None,
    mov_canonical: Path | None,
    index_file: Path,
    ia_key: str,
    ia_secret: str,
) -> list[str]:
    """Publish artifacts in dependency order, then the commit bundle last.

    The daily ZIP goes first because the index points into it; the canonical
    Parquets and the index follow; the bundle (with the advanced cursor) is
    only uploaded once all of them succeeded. Any failure raises and leaves the
    previously published bundle — and therefore the previous cursor — intact.
    """
    uploaded: list[str] = []
    data_paths: dict[str, Path] = {}
    ordered = [daily_zip_path, capa_canonical, mov_canonical, index_file]
    for path in ordered:
        if path is None or not path.exists():
            continue
        _upload_or_raise(path, tribunal, ia_key, ia_secret)
        uploaded.append(path.name)
        if path is not daily_zip_path:
            data_paths[path.name] = path

    checkpoint.status = "published"
    bundle_content, generation = cdc_state.build_bundle(checkpoint, data_paths, tribunal)
    bundle_path = index_file.parent / cdc_state.bundle_name(tribunal)
    bundle_path.write_bytes(bundle_content)
    try:
        _upload_or_raise(bundle_path, tribunal, ia_key, ia_secret)
    except cdc_state.CdcStateError:
        checkpoint.status = "collected"
        raise
    finally:
        bundle_path.unlink(missing_ok=True)
    uploaded.append(bundle_path.name)
    log.info("datajud_cdc_published", tribunal=tribunal, generation=generation, files=uploaded)
    return uploaded
