"""Config→result service layer for ``tjro-juris``, free of Typer (RFC 0013 Fase 2).

``__main__.py`` owns argv parsing and echoing results; this module owns the
actual work — crawling, uploading, consolidating — so it can be called from
a future MCP tool or a different CLI framework without dragging Typer along.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import anyio
import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import structlog

from tjro_juris import archive as ia_archive
from tjro_juris.client import TIPOS, clean_html
from tjro_juris.crawler import crawl_all
from tjro_juris.dedup import consolidate_year
from tjro_juris.manifest import ManifestJuris, ManifestJurisEntry


if TYPE_CHECKING:
    from pathlib import Path


log = structlog.get_logger()

_MANIFEST_NAME = "tjro-juris-manifest.csv"
_PARTIAL_CACHE_DIRNAME = ".partial-cache"
_MIN_DATE_LEN = 10

_PARQUET_SCHEMA = pa.schema(
    [
        pa.field("id_documento", pa.int64()),
        pa.field("nr_processo", pa.string()),
        pa.field("tipo", pa.string()),
        pa.field("classe_judicial", pa.string()),
        pa.field("orgao", pa.string()),
        pa.field("relator", pa.string()),
        pa.field("sistema_origem", pa.string()),
        pa.field("data_julgamento", pa.date32()),
        pa.field("texto_limpo", pa.string()),
        pa.field("url_portal", pa.string()),
        pa.field("extraido_em", pa.string()),
    ]
)


_MES_RE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")

DEFAULT_START_YEAR = 2010

# JURIS's own data goes further back than the crawler's original hardcoded
# default: live probes (2026-07-14) found DECISÃO from 1989, ACÓRDÃO from
# 1991, and SENTENÇA from 2007 — years before the old start_year=2010 default
# silently never crawled. --desde-ano lets a full backfill start earlier
# without changing the default (incremental/scheduled runs stay cheap).

_UPLOAD_INTERVAL_S = 1.0
# IA's S3-compatible endpoint 503s ("Slow Down") under sustained upload
# volume even WITH per-file retry/backoff (see tjro_juris.archive) — observed
# live during the historical backfill, where a whole year's worth of
# monthly parquets landed back-to-back with zero delay between PUTs. A
# small self-imposed pause between uploads mirrors the crawler's own
# _REQUEST_INTERVAL rate-limiting and cuts how often the retry path is
# needed at all, instead of just reacting to it after the fact.


def manifest_path(data_dir: Path) -> Path:
    """Path to the local manifest CSV under *data_dir*."""
    return data_dir / _MANIFEST_NAME


def _partial_cache_dir(data_dir: Path) -> Path:
    """Staging area for in-progress pagination (see crawler._fetch_pages).

    Lives under data_dir so it survives between crawl invocations of the
    same --ano; never uploaded to IA, never read by anything except a
    resumed crawl of the same window.
    """
    return data_dir / _PARTIAL_CACHE_DIRNAME


def load_manifest(data_dir: Path) -> ManifestJuris:
    """Load the local manifest, restoring it from IA when absent.

    A blank runner (CI) starts with no local state; without the restore every
    scheduled run would re-crawl and re-upload everything. The restore is
    best-effort: IA can return a transient error (observed: 503, not 404, for
    an item that has simply never been created yet) for reasons that have
    nothing to do with whether a manifest actually exists. Failing to
    restore only costs a redundant re-crawl of already-uploaded windows —
    no data is lost — so it must never abort the whole run.
    """
    path = manifest_path(data_dir)
    if not path.exists():
        try:
            ia_archive.download_manifest(path)
        except httpx.HTTPError as exc:
            log.warning("manifest_restore_failed", error=str(exc))
    return ManifestJuris.load_local(path)


def _should_skip_window(
    manifest: ManifestJuris, current_ym: str, tipo_name: str, year_month: str
) -> bool:
    """Skip a (tipo, year_month) window the manifest already records as uploaded.

    The current month is never skipped: JURIS keeps publishing into it, so it
    must always be re-crawled even if a previous run already uploaded it.
    """
    if year_month >= current_ym:
        return False
    entry = manifest.get(tipo_name, year_month)
    return entry is not None and entry.ia_status == "uploaded"


def crawl_bounds(
    ano: int | None, mes: str | None, desde_ano: int | None, now: datetime
) -> tuple[int, str | None, str | None]:
    """Resolve (start_year, end_year_month, start_year_month) for the crawl."""
    exclusive = [v is not None for v in (ano, mes, desde_ano)]
    if sum(exclusive) > 1:
        msg = "--ano, --mes and --desde-ano are mutually exclusive"
        raise ValueError(msg)
    if mes is not None:
        if not _MES_RE.fullmatch(mes):
            msg = f"--mes must be AAAA-MM, got {mes!r}"
            raise ValueError(msg)
        return int(mes[:4]), mes, mes
    if ano is not None:
        end = f"{ano:04d}-12" if ano < now.year else now.strftime("%Y-%m")
        return ano, end, None
    if desde_ano is not None:
        return desde_ano, None, None
    return DEFAULT_START_YEAR, None, None


def parquet_path(data_dir: Path, tipo: str, year_month: str) -> Path:
    """Path to the monthly parquet for a (tipo, year_month) window."""
    year = year_month[:4]
    safe_tipo = tipo.replace(" ", "_").replace("/", "_")
    return data_dir / year / safe_tipo / f"{year_month}.parquet"


def _normalize_date(dt_raw: str) -> str | None:
    """Normalize date string to YYYY-MM-DD."""
    if not dt_raw:
        return None
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", dt_raw)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return dt_raw[:_MIN_DATE_LEN] if len(dt_raw) >= _MIN_DATE_LEN else dt_raw


def _to_row(src: dict) -> dict:
    """Map a crawler-normalized doc to canonical parquet schema.

    Accepts the dict produced by crawler._extract_doc() which already uses
    canonical field names (id_documento, classe_judicial, orgao, etc.).
    """
    dt_raw = src.get("data_julgamento") or ""
    return {
        "id_documento": src.get("id_documento"),
        "nr_processo": src.get("nr_processo") or "",
        "tipo": src.get("tipo") or "",
        "classe_judicial": src.get("classe_judicial") or "",
        "orgao": src.get("orgao") or "",
        "relator": src.get("relator") or "",
        "sistema_origem": src.get("sistema_origem") or "",
        "data_julgamento": _normalize_date(dt_raw),
        "texto_limpo": src.get("texto_limpo") or clean_html(src.get("ds_modelo_documento") or ""),
        "url_portal": src.get("url_portal") or "",
        "extraido_em": src.get("extraido_em") or datetime.now(UTC).isoformat(),
    }


def _parse_date(v: str | None) -> _dt.date | None:
    """Parse ISO date string to date object."""
    if not v:
        return None
    try:
        return _dt.date.fromisoformat(v)
    except ValueError:
        return None


def _rows_to_parquet(rows: list[dict], out: Path) -> None:
    """Write list of row dicts to a parquet file using pyarrow."""
    arrays: dict[str, list] = {f.name: [] for f in _PARQUET_SCHEMA}
    for row in rows:
        for field in _PARQUET_SCHEMA:
            val = row.get(field.name)
            if field.name == "id_documento":
                arrays[field.name].append(int(val) if val is not None else None)
            elif field.name == "data_julgamento":
                arrays[field.name].append(val)
            else:
                arrays[field.name].append(str(val) if val is not None else None)

    arrow_cols = []
    for field in _PARQUET_SCHEMA:
        raw = arrays[field.name]
        if field.type == pa.date32():
            arrow_cols.append(pa.array([_parse_date(v) for v in raw], type=pa.date32()))
        else:
            arrow_cols.append(pa.array(raw, type=field.type))

    table = pa.table(
        dict(zip(_PARQUET_SCHEMA.names, arrow_cols, strict=True)), schema=_PARQUET_SCHEMA
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out)


def crawl_juris(
    data_dir: Path,
    tipo: list[str] | None,
    ano: int | None,
    mes: str | None,
    desde_ano: int | None,
) -> None:
    """Crawl JURIS and save as parquet files per (tipo, mes_ano).

    Windows already uploaded to IA (per the manifest, restored from IA when
    no local copy exists) are skipped, except the current month, which is
    always re-crawled to pick up newly published documents. Windows whose
    parquet is already on local disk (e.g. a prior attempt this same year
    got partway through before failing) are also skipped — see
    ``_already_crawled_locally``.

    The manifest is saved after EVERY window, not just once at the end: a
    long --ano/--desde-ano crawl that dies partway through (observed live —
    TJRO's STIC anti-abuse system can block a sustained crawl mid-year)
    previously lost all of that year's progress from the manifest even
    though the parquet files were already safely on disk, forcing a full
    re-fetch of every tipo on the next attempt. Saving incrementally means
    a retry only has to redo whatever wasn't finished yet.

    Raises ``ValueError`` when --ano/--mes/--desde-ano are combined, or
    --mes isn't AAAA-MM (see ``crawl_bounds``).
    """
    manifest = load_manifest(data_dir)
    tipos_to_crawl = tipo or TIPOS

    now = datetime.now(UTC)
    current_ym = now.strftime("%Y-%m")
    start_year, end_year_month, start_year_month = crawl_bounds(ano, mes, desde_ano, now)

    def _already_crawled_locally(tipo_name: str, year_month: str) -> bool:
        return parquet_path(data_dir, tipo_name, year_month).exists()

    def _skip(tipo_name: str, year_month: str) -> bool:
        if _already_crawled_locally(tipo_name, year_month):
            return True
        return _should_skip_window(manifest, current_ym, tipo_name, year_month)

    for tipo_name, year_month, docs in crawl_all(
        start_year=start_year,
        end_year_month=end_year_month,
        tipos=tipos_to_crawl,
        start_year_month=start_year_month,
        skip=_skip,
        cache_dir=_partial_cache_dir(data_dir),
        shuffle=True,
    ):
        if not docs:
            continue

        rows = [_to_row(d) for d in docs]
        out = parquet_path(data_dir, tipo_name, year_month)
        _rows_to_parquet(rows, out)
        log.info("parquet_saved", path=str(out), rows=len(rows))

        entry = ManifestJurisEntry(
            tipo=tipo_name,
            mes_ano=year_month,
            ia_status="",
            n_docs=len(docs),
        )
        manifest.upsert(entry)
        manifest.save_local(manifest_path(data_dir))

    log.info("crawl_done")


async def upload_pending(data_dir: Path) -> int:
    """Upload parquets (and the manifest) to Internet Archive. Returns the pending count."""
    manifest = load_manifest(data_dir)
    pending = manifest.pending_upload()

    for i, entry in enumerate(pending):
        if i > 0:
            await asyncio.sleep(_UPLOAD_INTERVAL_S)
        pq_path = parquet_path(data_dir, entry.tipo, entry.mes_ano)
        if not await anyio.Path(pq_path).exists():
            log.warning("parquet_not_found", path=str(pq_path))
            continue
        year = int(entry.mes_ano[:4])
        safe_tipo = entry.tipo.replace(" ", "_").replace("/", "_")
        remote_name = f"{entry.mes_ano}-{safe_tipo}.parquet"
        try:
            await ia_archive.upload_file(pq_path, year, remote_name)
            entry.ia_status = "uploaded"
            manifest.upsert(entry)
        except (httpx.HTTPError, httpx.RequestError, RuntimeError) as exc:
            log.warning(
                "upload_failed",
                entry=f"{entry.tipo}/{entry.mes_ano}",
                error=str(exc),
            )

    manifest.save_local(manifest_path(data_dir))
    try:
        await ia_archive.upload_manifest(manifest_path(data_dir))
    except (httpx.HTTPError, RuntimeError) as exc:
        # Non-fatal: parquets are already on IA; the next run just re-uploads.
        log.warning("manifest_upload_failed", error=str(exc))
    log.info("upload_done", pending=len(pending))
    return len(pending)


@dataclass
class ManifestStatus:
    """Summary counts for the local manifest."""

    total: int
    uploaded: int

    @property
    def pending(self) -> int:
        """Entries not yet uploaded."""
        return self.total - self.uploaded


def manifest_status(data_dir: Path) -> ManifestStatus:
    """Summarize the local manifest: total entries and how many are uploaded."""
    manifest = ManifestJuris.load_local(manifest_path(data_dir))
    entries = manifest.all_entries()
    uploaded = sum(1 for e in entries if e.ia_status == "uploaded")
    return ManifestStatus(total=len(entries), uploaded=uploaded)


def consolidate_parquets(data_dir: Path, year: int) -> tuple[Path, int]:
    """Consolidate monthly parquets for a year into a single deduplicated file."""
    parquet_files: list[Path] = []
    for tipo_name in TIPOS:
        safe_tipo = tipo_name.replace(" ", "_").replace("/", "_")
        tipo_dir = data_dir / str(year) / safe_tipo
        if tipo_dir.exists():
            parquet_files.extend(sorted(tipo_dir.glob("*.parquet")))

    output = data_dir / str(year) / f"tjro-juris-{year}.parquet"
    count = consolidate_year(parquet_files, output)
    return output, count
