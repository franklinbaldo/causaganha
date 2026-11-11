"""Historical backlog ingestion pipeline for DataJud.

Divides multi-year court archives into resilient, time-boxed slices (by year/month),
with granular SQLite resumption tokens and progressive annual Parquet publication.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from datajud import archive
from datajud.cdc import (
    DEFAULT_CANONICAL_DIR,
    DEFAULT_CDC_DIR,
    compact_deltas,
    write_delta_batch,
)
from datajud.client import DataJudClient
from datajud.daily_pack import (
    DEFAULT_DAILY_DIR,
    DEFAULT_INDEX_DIR,
    pack_daily_zip,
    update_resolution_index,
)


if TYPE_CHECKING:
    pass


log = structlog.get_logger()

DEFAULT_BACKLOG_DIR = Path("data/datajud/backlog")


@dataclass
class BacklogSlice:
    """A bounded temporal partition of historical data (e.g. 2024-05 or 2026-01-21)."""

    tribunal: str
    ano: int
    mes: int  # 0 = entire year
    data_inicio: str
    data_fim: str
    status: str = "pending"  # "pending", "in_progress", "completed", "error"
    search_after_cursor: list[Any] | None = None
    documentos_coletados: int = 0
    batches_coletados: int = 0
    tentativas: int = 0
    ultimo_erro: str | None = None
    atualizado_em: str = ""
    dia: int = 0  # 0 = entire month or entire year


class DataJudBacklogStore:
    """Thread-safe SQLite store for time-boxed backlog slices."""

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
                CREATE TABLE IF NOT EXISTS datajud_backlog_slices (
                    tribunal TEXT NOT NULL,
                    ano INTEGER NOT NULL,
                    mes INTEGER NOT NULL,
                    dia INTEGER NOT NULL DEFAULT 0,
                    data_inicio TEXT NOT NULL,
                    data_fim TEXT NOT NULL,
                    status TEXT NOT NULL,
                    search_after_cursor TEXT,
                    documentos_coletados INTEGER NOT NULL DEFAULT 0,
                    batches_coletados INTEGER NOT NULL DEFAULT 0,
                    tentativas INTEGER NOT NULL DEFAULT 0,
                    ultimo_erro TEXT,
                    atualizado_em TEXT NOT NULL,
                    PRIMARY KEY (tribunal, ano, mes, dia)
                );
                """
            )

    def init_slices(
        self,
        tribunal: str,
        start_year: int,
        end_year: int,
        *,
        slice_by: str = "month",
    ) -> list[BacklogSlice]:
        """Generate and insert pending slices for the given year range."""
        tribunal_slug = tribunal.lower()
        slices: list[BacklogSlice] = []
        now_iso = datetime.now(UTC).isoformat(timespec="seconds")

        for year in range(start_year, end_year + 1):
            if slice_by == "year":
                slices.append(
                    BacklogSlice(
                        tribunal=tribunal_slug,
                        ano=year,
                        mes=0,
                        dia=0,
                        data_inicio=f"{year}0101000000",
                        data_fim=f"{year}1231235959",
                        atualizado_em=now_iso,
                    )
                )
            elif slice_by == "day":
                for month in range(1, 13):
                    if month in (1, 3, 5, 7, 8, 10, 12):
                        last_day = 31
                    elif month in (4, 6, 9, 11):
                        last_day = 30
                    else:
                        last_day = (
                            29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
                        )

                    for day in range(1, last_day + 1):
                        slices.append(
                            BacklogSlice(
                                tribunal=tribunal_slug,
                                ano=year,
                                mes=month,
                                dia=day,
                                data_inicio=f"{year}{month:02d}{day:02d}000000",
                                data_fim=f"{year}{month:02d}{day:02d}235959",
                                atualizado_em=now_iso,
                            )
                        )
            else:
                for month in range(1, 13):
                    # Compute end day of month
                    if month in (1, 3, 5, 7, 8, 10, 12):
                        last_day = 31
                    elif month in (4, 6, 9, 11):
                        last_day = 30
                    else:
                        last_day = (
                            29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
                        )

                    slices.append(
                        BacklogSlice(
                            tribunal=tribunal_slug,
                            ano=year,
                            mes=month,
                            dia=0,
                            data_inicio=f"{year}{month:02d}01000000",
                            data_fim=f"{year}{month:02d}{last_day:02d}235959",
                            atualizado_em=now_iso,
                        )
                    )

        with self._get_connection() as conn:
            for s in slices:
                conn.execute(
                    """
                    INSERT INTO datajud_backlog_slices (
                        tribunal, ano, mes, dia, data_inicio, data_fim, status,
                        search_after_cursor, documentos_coletados, batches_coletados,
                        tentativas, ultimo_erro, atualizado_em
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(tribunal, ano, mes, dia) DO NOTHING;
                    """,
                    (
                        s.tribunal,
                        s.ano,
                        s.mes,
                        s.dia,
                        s.data_inicio,
                        s.data_fim,
                        s.status,
                        None,
                        s.documentos_coletados,
                        s.batches_coletados,
                        s.tentativas,
                        s.ultimo_erro,
                        s.atualizado_em,
                    ),
                )
        return self.list_slices(tribunal_slug)

    def get_slice(
        self, tribunal: str, ano: int, mes: int, dia: int = 0
    ) -> BacklogSlice | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM datajud_backlog_slices WHERE tribunal = ? AND ano = ? AND mes = ? AND dia = ?",
                (tribunal.lower(), ano, mes, dia),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_slice(row)

    def get_next_pending_slice(self, tribunal: str) -> BacklogSlice | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM datajud_backlog_slices
                WHERE tribunal = ? AND status IN ('pending', 'in_progress')
                ORDER BY ano DESC, mes DESC, dia DESC
                LIMIT 1;
                """,
                (tribunal.lower(),),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_slice(row)

    def update_slice(self, s: BacklogSlice) -> None:
        cursor_json = (
            json.dumps(s.search_after_cursor) if s.search_after_cursor is not None else None
        )
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE datajud_backlog_slices SET
                    status = ?,
                    search_after_cursor = ?,
                    documentos_coletados = ?,
                    batches_coletados = ?,
                    tentativas = ?,
                    ultimo_erro = ?,
                    atualizado_em = ?
                WHERE tribunal = ? AND ano = ? AND mes = ? AND dia = ?;
                """,
                (
                    s.status,
                    cursor_json,
                    s.documentos_coletados,
                    s.batches_coletados,
                    s.tentativas,
                    s.ultimo_erro,
                    datetime.now(UTC).isoformat(timespec="seconds"),
                    s.tribunal.lower(),
                    s.ano,
                    s.mes,
                    s.dia,
                ),
            )

    def list_slices(self, tribunal: str) -> list[BacklogSlice]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM datajud_backlog_slices WHERE tribunal = ? ORDER BY ano DESC, mes DESC, dia DESC",
                (tribunal.lower(),),
            ).fetchall()
            return [self._row_to_slice(r) for r in rows]

    @staticmethod
    def _row_to_slice(row: sqlite3.Row) -> BacklogSlice:
        cursor = (
            json.loads(row["search_after_cursor"])
            if row["search_after_cursor"] is not None
            else None
        )
        dia = row["dia"] if "dia" in row.keys() else 0
        return BacklogSlice(
            tribunal=row["tribunal"],
            ano=row["ano"],
            mes=row["mes"],
            dia=dia,
            data_inicio=row["data_inicio"],
            data_fim=row["data_fim"],
            status=row["status"],
            search_after_cursor=cursor,
            documentos_coletados=row["documentos_coletados"],
            batches_coletados=row["batches_coletados"],
            tentativas=row["tentativas"],
            ultimo_erro=row["ultimo_erro"],
            atualizado_em=row["atualizado_em"],
        )


async def run_backlog_slice(
    slice_item: BacklogSlice,
    store: DataJudBacklogStore,
    *,
    page_size: int = 1000,
    min_page_size: int = 100,
    max_pages: int | None = None,
    pause_between_pages: float = 0.5,
    base_dir: Path = DEFAULT_CDC_DIR,
    daily_dir: Path = DEFAULT_DAILY_DIR,
    index_dir: Path = DEFAULT_INDEX_DIR,
    client: DataJudClient | None = None,
) -> tuple[int, int]:
    """Execute one backlog slice, writing deltas and updating the slice checkpoint."""
    tribunal_slug = slice_item.tribunal.lower()
    deltas_dir = base_dir / "deltas"

    slice_item.status = "in_progress"
    slice_item.tentativas += 1
    store.update_slice(slice_item)

    own_client = client is None
    active_client = client or DataJudClient(tribunal=tribunal_slug)

    session_docs: list[dict[str, Any]] = []

    try:
        if own_client:
            await active_client.__aenter__()

        part_seq = slice_item.batches_coletados

        async for batch_hits, last_sort in active_client.iter_updated_since(
            since_iso=slice_item.data_inicio,
            until_iso=slice_item.data_fim,
            range_field="dataAjuizamento",
            page_size=page_size,
            min_page_size=min_page_size,
            max_pages=max_pages,
            pause_between_pages=pause_between_pages,
            search_after=slice_item.search_after_cursor,
        ):
            part_seq += 1
            session_docs.extend(batch_hits)

            # Write L1 Delta Parquet
            write_delta_batch(batch_hits, tribunal_slug, part_seq, deltas_dir)

            # Update slice store checkpoint
            slice_item.search_after_cursor = last_sort
            slice_item.documentos_coletados += len(batch_hits)
            slice_item.batches_coletados = part_seq
            store.update_slice(slice_item)

            log.info(
                "datajud_backlog_slice_progress",
                tribunal=tribunal_slug,
                ano=slice_item.ano,
                mes=slice_item.mes,
                dia=slice_item.dia,
                batch_seq=part_seq,
                batch_size=len(batch_hits),
                total=slice_item.documentos_coletados,
            )

        slice_item.status = "completed"
        slice_item.ultimo_erro = None
        store.update_slice(slice_item)

        # Pack completed slice processes into a ZIP
        if session_docs:
            if slice_item.dia:
                label = f"{slice_item.ano}_{slice_item.mes:02d}_{slice_item.dia:02d}"
            elif slice_item.mes:
                label = f"{slice_item.ano}_{slice_item.mes:02d}"
            else:
                label = f"{slice_item.ano}"
            zip_path, _ = pack_daily_zip(
                session_docs,
                tribunal_slug,
                target_date=label,
                output_dir=daily_dir,
            )
            index_path = index_dir / f"indice_processos_{tribunal_slug}.parquet"
            update_resolution_index(
                index_path,
                session_docs,
                zip_path.name,
                tribunal=tribunal_slug,
            )

    except Exception as exc:  # per-slice bulkhead, see docs/adr/0011
        slice_item.status = "error"
        slice_item.ultimo_erro = str(exc)
        store.update_slice(slice_item)
        log.exception(
            "datajud_backlog_slice_failed",
            tribunal=tribunal_slug,
            ano=slice_item.ano,
            mes=slice_item.mes,
            dia=slice_item.dia,
            error=str(exc),
        )
        raise

    finally:
        if own_client:
            await active_client.__aexit__(None, None, None)

    return slice_item.documentos_coletados, slice_item.batches_coletados


async def run_backlog(
    tribunal: str,
    start_year: int,
    end_year: int,
    *,
    slice_by: str = "month",
    max_slices: int | None = None,
    page_size: int = 1000,
    consolidate: bool = True,
    upload: bool = False,
    base_dir: Path = DEFAULT_BACKLOG_DIR,
    canonical_dir: Path = DEFAULT_CANONICAL_DIR,
    daily_dir: Path = DEFAULT_DAILY_DIR,
    index_dir: Path = DEFAULT_INDEX_DIR,
    ia_key: str = "",
    ia_secret: str = "",
    client: DataJudClient | None = None,
) -> dict[str, Any]:
    """Orchestrate multi-year backlog ingestion across time-boxed slices."""
    tribunal_slug = tribunal.lower()
    store = DataJudBacklogStore(base_dir / "backlog_slices.sqlite")

    # Initialize slices if not present
    store.init_slices(tribunal_slug, start_year, end_year, slice_by=slice_by)

    slices_processed = 0
    total_docs = 0

    while True:
        if max_slices is not None and slices_processed >= max_slices:
            break

        pending_slice = store.get_next_pending_slice(tribunal_slug)
        if pending_slice is None:
            log.info("datajud_backlog_all_slices_done", tribunal=tribunal_slug)
            break

        log.info(
            "datajud_backlog_starting_slice",
            tribunal=tribunal_slug,
            ano=pending_slice.ano,
            mes=pending_slice.mes,
            dia=pending_slice.dia,
        )

        docs, _ = await run_backlog_slice(
            pending_slice,
            store,
            page_size=page_size,
            base_dir=base_dir,
            daily_dir=daily_dir,
            index_dir=index_dir,
            client=client,
        )

        slices_processed += 1
        total_docs += docs

    # Consolidate into canonical Parquet
    if consolidate:
        compact_deltas(
            tribunal_slug,
            deltas_dir=base_dir / "deltas",
            canonical_dir=canonical_dir,
        )

    # Upload to Internet Archive if credentials provided
    uploaded: list[str] = []
    if upload and ia_key and ia_secret:
        capa_path = canonical_dir / archive.capa_parquet_name(tribunal_slug)
        mov_path = canonical_dir / archive.movimentos_parquet_name(tribunal_slug)
        index_file = index_dir / f"indice_processos_{tribunal_slug}.parquet"

        for p in [capa_path, mov_path, index_file]:
            if p.exists() and archive.upload_file(p, tribunal_slug, ia_key, ia_secret):
                uploaded.append(p.name)

    return {
        "tribunal": tribunal_slug,
        "slices_processed": slices_processed,
        "total_documents": total_docs,
        "uploaded_files": uploaded,
    }
