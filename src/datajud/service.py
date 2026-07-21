"""Config→result service layer for ``datajud``, free of Typer/echo (RFC 0013 Fase 2).

``__main__.py`` owns argv parsing and echoing results; this module owns the
actual work — gathering CNJs, fetching/persisting capa+movimentos, uploading
— so it can be called from a future MCP tool or a different CLI framework
without dragging Typer along. Also drops ``ia_key``/``ia_secret`` as CLI
options: Internet Archive credentials are read from the environment only
(``ia_credentials``), never exposed as a parameter a schema (CLI or future
MCP tool) could carry.
"""

from __future__ import annotations

import asyncio
import os
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
import structlog
from pydantic import ValidationError

from datajud import archive
from datajud.client import DataJudClient, DataJudError
from datajud.dedup import capa_row_key, dedup_capas, merge_capa_rows, merge_movimento_rows
from datajud.manifest import STATUS_OK, ManifestDataJud
from datajud.models import ProcessoCapa, normalizar_cnj


log = structlog.get_logger()

DEFAULT_DATA_DIR = Path("data/datajud")
DEFAULT_SOURCES_DIR = Path("data")
MANIFEST_NAME = "datajud-manifest.csv"

UNIFICADOS_IA_URL = "https://archive.org/download/causaganha-dashboard/processos_unificados.parquet"


def manifest_path(data_dir: Path) -> Path:
    """Path to the local manifest CSV under *data_dir*."""
    return data_dir / MANIFEST_NAME


def ia_credentials() -> tuple[str, str]:
    """Read Internet Archive S3 credentials from the environment."""
    return os.environ.get("IA_ACCESS_KEY", ""), os.environ.get("IA_SECRET_KEY", "")


# ── CNJ sources ──────────────────────────────────────────────────────────


def _read_cnj_file(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _source_selects(sources_dir: Path) -> list[str]:
    selects: list[str] = []
    unificados = sources_dir / "processos_unificados.parquet"
    if unificados.exists():
        selects.append(f"SELECT nr_processo AS cnj FROM read_parquet('{unificados}')")
    juris_files = sorted(sources_dir.glob("tjro-juris/*/tjro-juris-*.parquet"))
    if juris_files:
        juris_list = ", ".join(f"'{p}'" for p in juris_files)
        selects.append(f"SELECT nr_processo AS cnj FROM read_parquet([{juris_list}])")
    stj = sources_dir / "stj" / "stj-acordaos.parquet"
    if stj.exists():
        selects.append(f"SELECT \"numeroProcesso\" AS cnj FROM read_parquet('{stj}')")
    return selects


def _try_download_unificados(sources_dir: Path) -> None:
    """Best-effort download of processos_unificados from IA (CI cold start)."""
    dest = sources_dir / "processos_unificados.parquet"
    log.info("datajud_downloading_unificados", url=UNIFICADOS_IA_URL)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(UNIFICADOS_IA_URL, timeout=180) as resp:  # noqa: S310
            dest.write_bytes(resp.read())
    except OSError as exc:
        log.warning("datajud_unificados_download_failed", error=str(exc))


def _collect_source_cnjs(sources_dir: Path) -> list[str]:
    """Distinct valid CNJs from the local source parquets (RFC 0010 §2)."""
    import duckdb

    selects = _source_selects(sources_dir)
    if not selects:
        _try_download_unificados(sources_dir)
        selects = _source_selects(sources_dir)
    if not selects:
        return []
    union = " UNION ALL ".join(selects)
    sql = (
        "SELECT DISTINCT regexp_replace(cnj, '[^0-9]', '', 'g') AS cnj "
        f"FROM ({union}) "
        "WHERE length(regexp_replace(cnj, '[^0-9]', '', 'g')) = 20 ORDER BY cnj"
    )
    con = duckdb.connect()
    try:
        rows = con.execute(sql).fetchall()
    finally:
        con.close()
    return [row[0] for row in rows]


def gather_cnjs(cnj: list[str] | None, cnj_file: Path | None, sources_dir: Path) -> list[str]:
    """Resolve the CNJs to consult: explicit --cnj/--cnj-file, else local source parquets."""
    explicit: list[str] = list(cnj or [])
    if cnj_file is not None:
        explicit.extend(_read_cnj_file(cnj_file))
    if explicit:
        return explicit
    return _collect_source_cnjs(sources_dir)


# ── Parquet round-trip ───────────────────────────────────────────────────


def _read_parquet_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    import duckdb

    con = duckdb.connect()
    try:
        cursor = con.execute(f"SELECT * FROM read_parquet('{path}')")
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
    finally:
        con.close()


# ── Fetch ────────────────────────────────────────────────────────────────


async def fetch_capas(cnjs: list[str], tribunal: str, batch_size: int) -> list[ProcessoCapa]:
    """Fetch capa+movimentos for *cnjs* from the DataJud API."""
    async with DataJudClient(tribunal=tribunal, batch_size=batch_size) as client:
        sources = await client.fetch_processos(cnjs)
    capas: list[ProcessoCapa] = []
    for source in sources:
        try:
            capas.append(ProcessoCapa.from_source(source))
        except ValidationError as exc:
            log.warning(
                "datajud_malformed_document",
                error=str(exc),
                numero_processo=source.get("numeroProcesso"),
            )
    return capas


def persist(
    capas: list[ProcessoCapa],
    tribunal: str,
    data_dir: Path,
) -> tuple[Path, Path, int, int]:
    """Merge fresh capas into the tribunal parquets. Returns paths + counts."""
    consultado_em = datetime.now(UTC).isoformat(timespec="seconds")
    new_capa_rows = [c.capa_row(tribunal=tribunal, consultado_em=consultado_em) for c in capas]
    new_mov_rows = [row for c in capas for row in c.movimento_rows(tribunal=tribunal)]
    refreshed_keys = {capa_row_key(row) for row in new_capa_rows}

    capa_path = data_dir / archive.capa_parquet_name(tribunal)
    mov_path = data_dir / archive.movimentos_parquet_name(tribunal)
    capa_rows = merge_capa_rows(_read_parquet_rows(capa_path), new_capa_rows)
    mov_rows = merge_movimento_rows(_read_parquet_rows(mov_path), new_mov_rows, refreshed_keys)

    n_capa = archive.write_capa_parquet(capa_rows, capa_path)
    n_mov = archive.write_movimentos_parquet(mov_rows, mov_path)
    return capa_path, mov_path, n_capa, n_mov


@dataclass
class UploadResult:
    """Result of ``upload_parquets``."""

    ok: bool
    failed_file: str | None = None


def upload_parquets(paths: list[Path], tribunal: str, ia_key: str, ia_secret: str) -> UploadResult:
    """Upload *paths* to the ``datajud-{tribunal}`` IA item, stopping at the first failure."""
    for path in paths:
        log.info("datajud_uploading", file=path.name, item=archive.item_id(tribunal))
        if not archive.upload_parquet(path, tribunal, ia_key, ia_secret):
            return UploadResult(ok=False, failed_file=path.name)
    return UploadResult(ok=True)


@dataclass
class EnrichResult:
    """Result of ``enrich``."""

    status: Literal[
        "no_cnjs",
        "nothing_to_do",
        "fetch_error",
        "missing_credentials",
        "upload_error",
        "done",
    ]
    error: str = ""
    pending: list[str] = field(default_factory=list)
    capa_path: Path | None = None
    mov_path: Path | None = None
    n_capa: int = 0
    n_mov: int = 0
    manifest_entries: int = 0


def _upload_step(
    capa_path: Path,
    mov_path: Path,
    tribunal: str,
    ia_key: str,
    ia_secret: str,
) -> tuple[Literal["missing_credentials", "upload_error"], str] | None:
    """Attempt the IA upload for ``enrich``; returns ``(status, error)`` on failure, else None."""
    if not ia_key or not ia_secret:
        return "missing_credentials", ""
    result = upload_parquets([capa_path, mov_path], tribunal, ia_key, ia_secret)
    if not result.ok:
        return "upload_error", result.failed_file or ""
    return None


def _pending_cnjs(
    candidates: list[str],
    manifest: ManifestDataJud,
    tribunal: str,
    max_age_days: int,
    limit: int,
) -> list[str]:
    """Dedup *candidates* and keep only those stale per the manifest, capped at *limit*."""
    pending: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        norm = normalizar_cnj(raw)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        if manifest.needs_refresh(norm, tribunal, max_age_days=max_age_days):
            pending.append(norm)
    return pending[:limit] if limit > 0 else pending


def enrich(
    tribunal: str,
    data_dir: Path,
    sources_dir: Path,
    cnj: list[str] | None,
    cnj_file: Path | None,
    limit: int,
    max_age_days: int,
    batch_size: int,
    *,
    skip_upload: bool,
    ia_key: str,
    ia_secret: str,
) -> EnrichResult:
    """Consulta capa + movimentos dos CNJs pendentes e arquiva parquets no IA."""
    candidates = gather_cnjs(cnj, cnj_file, sources_dir)
    if not candidates:
        return EnrichResult(status="no_cnjs")

    manifest = ManifestDataJud.load_local(manifest_path(data_dir))
    pending = _pending_cnjs(candidates, manifest, tribunal, max_age_days, limit)

    if not pending:
        return EnrichResult(status="nothing_to_do")

    log.info("datajud_consulting", count=len(pending), tribunal=tribunal.upper())
    try:
        capas = dedup_capas(asyncio.run(fetch_capas(pending, tribunal, batch_size)))
    except (DataJudError, httpx.HTTPError) as exc:
        return EnrichResult(status="fetch_error", error=str(exc))

    capa_path, mov_path, n_capa, n_mov = persist(capas, tribunal, data_dir)

    # Mark the manifest fresh only after a successful upload (or an explicit
    # --skip-upload) — otherwise a failed IA push would be indistinguishable
    # from a completed one, and needs_refresh() would skip these CNJs for up
    # to max_age_days before the upload is ever retried.
    if not skip_upload:
        failure = _upload_step(capa_path, mov_path, tribunal, ia_key, ia_secret)
        if failure is not None:
            status, error = failure
            return EnrichResult(
                status=status,
                error=error,
                capa_path=capa_path,
                mov_path=mov_path,
                n_capa=n_capa,
                n_mov=n_mov,
            )

    found = Counter(capa.cnj for capa in capas)
    for consulted in pending:
        manifest.upsert(consulted, tribunal, docs=found.get(consulted, 0), status=STATUS_OK)
    manifest.save_local(manifest_path(data_dir))

    return EnrichResult(
        status="done",
        pending=pending,
        capa_path=capa_path,
        mov_path=mov_path,
        n_capa=n_capa,
        n_mov=n_mov,
        manifest_entries=len(manifest),
    )


async def facetas(tribunal: str, por: str, limite: int) -> tuple[int, list[dict]]:
    """Aggregate the acervo by *por* (classe/assunto/orgao/...) without downloading docs."""
    async with DataJudClient(tribunal=tribunal) as client:
        return await client.facetas(por, limite=limite)


@dataclass
class ManifestStatus:
    """Summary of the DataJud manifest for the ``status`` command."""

    total: int
    ok: int
    com_docs: int

    @property
    def sem_docs(self) -> int:
        """CNJs consulted successfully but with no documents found."""
        return self.ok - self.com_docs

    @property
    def com_erro(self) -> int:
        """CNJs whose last consult failed."""
        return self.total - self.ok


def manifest_status(data_dir: Path) -> ManifestStatus | None:
    """Summarize the local manifest, or None when it's empty/missing."""
    manifest = ManifestDataJud.load_local(manifest_path(data_dir))
    entries = manifest.all_entries()
    if not entries:
        return None
    ok = sum(1 for e in entries if e.status == STATUS_OK)
    com_docs = sum(1 for e in entries if e.status == STATUS_OK and e.docs > 0)
    return ManifestStatus(total=len(entries), ok=ok, com_docs=com_docs)
