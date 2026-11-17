"""Change Data Capture (CDC) engine for bulk/incremental DataJud sync and IA backup.

Implements the delta-based ingestion pipeline outlined in Issue #1701:
- Uses `DataJudClient.iter_updated_since` (search_after cursor pagination).
- Checkpointing in SQLite (resilient, atomic state resumption per tribunal).
- Writes raw incoming batches as L1 deltas in partitioned Parquet files.
- Consolidates L1 deltas into canonical L0 Parquet tables with natural key deduplication.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import structlog
from pydantic import ValidationError

from datajud import archive, cdc_state
from datajud.client import DataJudClient
from datajud.daily_pack import (
    DEFAULT_DAILY_DIR,
    DEFAULT_INDEX_DIR,
    SessionSpool,
    export_daily_locators,
    update_resolution_index,
)
from datajud.models import ProcessoCapa


if TYPE_CHECKING:
    from collections.abc import Sequence


log = structlog.get_logger()

DEFAULT_CDC_DIR = Path("data/datajud/cdc")
DEFAULT_CANONICAL_DIR = Path("data/datajud")
# DuckDB spills past this instead of growing RAM; the runner has 16 GB.
COMPACT_MEMORY_LIMIT = "4GB"


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


def _duckdb_connection(work_dir: Path) -> duckdb.DuckDBPyConnection:
    """In-process DuckDB that spills to *work_dir* instead of growing RAM."""
    work_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory = '{work_dir.as_posix()}'")
    con.execute(f"SET memory_limit = '{COMPACT_MEMORY_LIMIT}'")
    con.execute("SET preserve_insertion_order = false")
    return con


def _sql_list(paths: Sequence[Path]) -> str:
    return "[" + ", ".join("'" + p.as_posix().replace("'", "''") + "'" for p in paths) + "]"


def _kv_metadata_sql(tribunal: str) -> str:
    pairs = archive.kv_metadata_for_export(archive.item_id(tribunal))
    return "{" + ", ".join(f"'{k}': '{v}'" for k, v in pairs.items()) + "}"


def _select_columns(schema: pa.Schema, source: str) -> str:
    casts = {"string": "VARCHAR", "int64": "BIGINT"}
    return ", ".join(f"CAST({source}.{f.name} AS {casts[str(f.type)]}) AS {f.name}" for f in schema)


def _ordered_source(
    con: duckdb.DuckDBPyConnection,
    view: str,
    canonical: Path,
    deltas: Sequence[tuple[Path, int]],
    schema: pa.Schema,
) -> None:
    """View over canonical (``_ord`` 0) and deltas (``_ord`` = batch position).

    ``_row`` is the row position inside its file, so "later occurrence wins"
    keeps the exact tie-break of :func:`datajud.dedup.merge_capa_rows`.
    """
    files = ([(canonical, 0)] if canonical.exists() else []) + list(deltas)
    values = ", ".join(f"('{path.as_posix()}', {order})" for path, order in files)
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE {view}_files AS "
        f"SELECT * FROM (VALUES {values}) t(filename, _ord)"
    )
    con.execute(
        f"CREATE OR REPLACE TEMP VIEW {view} AS "
        f"SELECT {_select_columns(schema, 'r')}, f._ord, r.file_row_number AS _row "
        f"FROM read_parquet({_sql_list([path for path, _ in files])}, union_by_name = true, "
        "filename = true, file_row_number = true) r "
        f"JOIN {view}_files f ON r.filename = f.filename"
    )


# Capa natural key, identical to datajud.dedup.capa_row_key: codigo when
# present, else a namespaced nome fallback.
_CAPA_KEY = (
    "numero_processo, grau, "
    "COALESCE(CAST(orgao_julgador_codigo AS VARCHAR), 'nome:' || COALESCE(orgao_julgador, ''))"
)
# Movimento rows carry no órgão *name*, so their replacement key can only use
# the código. The old Python merge built "nome:" for them and "nome:<órgão>"
# for the capa, so movements of documents without a código were never
# replaced and piled up as duplicates on every refresh.
_MOV_KEY = "numero_processo, grau, orgao_julgador_codigo"


def compact_deltas(
    tribunal: str,
    *,
    deltas_dir: Path,
    canonical_dir: Path,
    clean_after_compact: bool = True,
) -> tuple[Path, Path, int, int]:
    """Merge all L1 delta Parquet files of *tribunal* into the canonical L0 Parquet tables.

    Runs entirely in DuckDB over the Parquet files (spilling to disk), so memory
    no longer grows with the size of the canonical tables (issue #1708).

    Semantics match the previous Python merge, applied delta by delta:

    * capa: per natural key the latest ``ultima_atualizacao`` wins; ties go to
      the later occurrence (later delta, later row);
    * movimentos: a document refreshed by any delta has its movements replaced
      wholesale by those of the last delta that refreshed it.

    Returns:
        (canonical_capa_path, canonical_mov_path, total_capa_rows, total_mov_rows)
    """
    tribunal_slug = tribunal.lower()
    trib_deltas_dir = deltas_dir / tribunal_slug

    canonical_dir.mkdir(parents=True, exist_ok=True)
    capa_canonical = canonical_dir / archive.capa_parquet_name(tribunal_slug)
    mov_canonical = canonical_dir / archive.movimentos_parquet_name(tribunal_slug)

    capa_delta_files = (
        sorted(trib_deltas_dir.glob("capa_delta_*.parquet")) if trib_deltas_dir.exists() else []
    )
    mov_delta_files = (
        sorted(trib_deltas_dir.glob("mov_delta_*.parquet")) if trib_deltas_dir.exists() else []
    )

    if not capa_delta_files and not mov_delta_files:
        return (
            capa_canonical,
            mov_canonical,
            _count_rows(capa_canonical),
            _count_rows(mov_canonical),
        )

    # Align capa/mov deltas by batch sequence so _ord means the same batch in both.
    seqs = sorted(
        {f.name.replace("capa_delta_", "") for f in capa_delta_files}
        | {f.name.replace("mov_delta_", "") for f in mov_delta_files}
    )
    capa_by_seq = {f.name.replace("capa_delta_", ""): f for f in capa_delta_files}
    mov_by_seq = {f.name.replace("mov_delta_", ""): f for f in mov_delta_files}

    work_dir = deltas_dir / f".duckdb-{tribunal_slug}"
    con = _duckdb_connection(work_dir)
    capa_tmp = capa_canonical.with_name(f".{capa_canonical.name}.tmp")
    mov_tmp = mov_canonical.with_name(f".{mov_canonical.name}.tmp")
    try:
        kv = _kv_metadata_sql(tribunal_slug)
        # _ord is the batch position, shared by the capa and mov delta of a batch.
        capa_seq_files = [(capa_by_seq[s], i) for i, s in enumerate(seqs, 1) if s in capa_by_seq]
        mov_seq_files = [(mov_by_seq[s], i) for i, s in enumerate(seqs, 1) if s in mov_by_seq]
        _ordered_source(con, "capa_src", capa_canonical, capa_seq_files, archive.CAPA_SCHEMA)
        _ordered_source(con, "mov_src", mov_canonical, mov_seq_files, archive.MOVIMENTOS_SCHEMA)
        capa_cols = ", ".join(archive.CAPA_SCHEMA.names)
        mov_cols = ", ".join(archive.MOVIMENTOS_SCHEMA.names)
        con.execute(
            f"COPY (SELECT {capa_cols} FROM ("
            f"  SELECT *, row_number() OVER (PARTITION BY {_CAPA_KEY} "
            "    ORDER BY COALESCE(ultima_atualizacao, '') DESC, _ord DESC, _row DESC) AS _rn"
            "  FROM capa_src) WHERE _rn = 1 "
            f"ORDER BY {_CAPA_KEY}"
            f") TO '{capa_tmp.as_posix()}' (FORMAT parquet, COMPRESSION zstd, KV_METADATA {kv})"
        )
        con.execute(
            "CREATE OR REPLACE TEMP TABLE refreshed AS "
            f"SELECT {_MOV_KEY}, max(_ord) AS last_ord FROM capa_src WHERE _ord > 0 "
            f"GROUP BY {_MOV_KEY}"
        )
        con.execute(
            f"COPY (SELECT {mov_cols} FROM ("
            f"  SELECT m.*, r.last_ord FROM mov_src m LEFT JOIN refreshed r "
            "    ON m.numero_processo = r.numero_processo AND m.grau IS NOT DISTINCT FROM r.grau "
            "    AND m.orgao_julgador_codigo IS NOT DISTINCT FROM r.orgao_julgador_codigo"
            ") WHERE last_ord IS NULL OR _ord = last_ord "
            "ORDER BY numero_processo, grau, COALESCE(data_hora, ''), codigo, nome"
            f") TO '{mov_tmp.as_posix()}' (FORMAT parquet, COMPRESSION zstd, KV_METADATA {kv})"
        )
    finally:
        con.close()
        shutil.rmtree(work_dir, ignore_errors=True)
    capa_tmp.replace(capa_canonical)
    mov_tmp.replace(mov_canonical)
    n_capa = _count_rows(capa_canonical)
    n_mov = _count_rows(mov_canonical)

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


def _count_rows(path: Path) -> int:
    return pq.ParquetFile(path).metadata.num_rows if path.exists() else 0


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
        spool = SessionSpool(base_dir / "session" / f"{tribunal_slug}.ndjson")
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
            spool.add(batch_hits)

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
    spool.close()
    try:
        if pack_daily and len(spool):
            # Run-unique name: a second run on the same day must not overwrite
            # the snapshot that the published index may still point to (#1707).
            target_date = datetime.now(UTC).strftime("%Y-%m-%dT%H%M%SZ")
            daily_zip_path, daily_count = spool.pack_zip(
                tribunal_slug, target_date=target_date, output_dir=daily_dir
            )
            index_path = index_dir / f"indice_processos_{tribunal_slug}.parquet"
            index_total = update_resolution_index(
                index_path,
                spool.index_documents(),
                daily_zip_path.name,
                tribunal=tribunal_slug,
            )
    finally:
        spool.path.unlink(missing_ok=True)

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
    # The locator sidecar (#1721) lists the members actually inside the daily
    # ZIP, so it is generated from the ZIP and published right after it, never
    # inferred from the one-row-per-CNJ resolution index.
    locators = None
    if daily_zip_path is not None and daily_zip_path.exists():
        try:
            locators = export_daily_locators(daily_zip_path, tribunal)
        except ValueError as exc:
            # A member without a verifiable identity cannot be published as a
            # locator; fail closed so the cursor does not advance past it.
            msg = f"cannot build DataJud locators for {daily_zip_path.name}: {exc}"
            raise cdc_state.CdcStateError(msg) from exc
    ordered = [daily_zip_path, locators, capa_canonical, mov_canonical, index_file]
    for path in ordered:
        if path is None or not path.exists():
            continue
        _upload_or_raise(path, tribunal, ia_key, ia_secret)
        uploaded.append(path.name)
        if path not in (daily_zip_path, locators):
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
    visible = cdc_state.await_bundle_visible(tribunal, bundle_content)
    log.info("datajud_cdc_bundle_visible", tribunal=tribunal, visible=visible)
    if not visible:
        log.warning(
            "datajud_cdc_bundle_not_yet_visible",
            tribunal=tribunal,
            hint="the next queued run may restore the previous generation and redo work",
        )
    return uploaded
