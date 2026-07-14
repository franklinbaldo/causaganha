"""TJRO JURIS CLI — crawl, upload, status, consolidate.

Manual execution
----------------
Crawl JURIS into monthly parquets (optionally windowed by year/month and tipo)::

    uv run tjro-juris crawl data/tjro-juris --ano 2024 --tipo "ACÓRDÃO" --tipo "SENTENÇA"
    uv run tjro-juris crawl data/tjro-juris --mes 2026-07   # incremental (current month)

Upload pending parquets to the yearly ``tjro-juris-{year}`` IA items
(requires ``IAS3_ACCESS_KEY`` / ``IAS3_SECRET_KEY`` in the environment)::

    uv run --env-file ~/workspace/.env tjro-juris upload data/tjro-juris

Show manifest status / consolidate a year into a single deduplicated parquet::

    uv run tjro-juris status data/tjro-juris
    uv run tjro-juris consolidate data/tjro-juris 2024

When no local manifest exists, ``crawl``/``upload`` first try to restore it
from the public IA item (``tjro-juris``); ``upload`` pushes it back so
scheduled runs on blank runners stay incremental.

In CI, ``.github/workflows/tjro-sync.yml`` runs the same commands hourly
(scheduled runs crawl only the current month) plus ``workflow_dispatch``.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import anyio
import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import structlog
import typer

from tjro_juris import archive as ia_archive
from tjro_juris.client import TIPOS, clean_html
from tjro_juris.crawler import crawl_all
from tjro_juris.dedup import consolidate_year
from tjro_juris.manifest import ManifestJuris, ManifestJurisEntry


log = structlog.get_logger()
app = typer.Typer(name="tjro-juris", help="TJRO JURIS scraping and archival.")

_MANIFEST_NAME = "tjro-juris-manifest.csv"
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
        # Added 2026-07-14 — see crawler._extract_doc for why these and not
        # the rest of the ~29 raw ES fields.
        pa.field("id_processo", pa.int64()),
        pa.field("cd_assunto_trf", pa.string()),
        pa.field("ds_assunto_trf", pa.string()),
        pa.field("cd_classe_judicial", pa.string()),
        pa.field("nivel_sigilo_processo", pa.int64()),
        pa.field("grau_jurisdicao", pa.int64()),
        pa.field("ds_md5_documento", pa.string()),
        pa.field("id_orgao_julgador", pa.int64()),
        pa.field("id_orgao_julgador_colegiado", pa.int64()),
    ]
)

# Parquet-typed as int64 in _PARQUET_SCHEMA above — _rows_to_parquet uses this
# to decide int-coercion vs plain string for every other field.
_INT_FIELD_NAMES = frozenset(
    {
        "id_documento",
        "id_processo",
        "nivel_sigilo_processo",
        "grau_jurisdicao",
        "id_orgao_julgador",
        "id_orgao_julgador_colegiado",
    }
)


_MES_RE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")


def _manifest_path(data_dir: Path) -> Path:
    return data_dir / _MANIFEST_NAME


def _load_manifest(data_dir: Path) -> ManifestJuris:
    """Load the local manifest, restoring it from IA when absent.

    A blank runner (CI) starts with no local state; without the restore every
    scheduled run would re-crawl and re-upload everything. The restore is
    best-effort: IA can return a transient error (observed: 503, not 404, for
    an item that has simply never been created yet) for reasons that have
    nothing to do with whether a manifest actually exists. Failing to
    restore only costs a redundant re-crawl of already-uploaded windows —
    no data is lost — so it must never abort the whole run.
    """
    path = _manifest_path(data_dir)
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


_DEFAULT_START_YEAR = 2010

# JURIS's own data goes further back than the crawler's original hardcoded
# default: live probes (2026-07-14) found DECISÃO from 1989, ACÓRDÃO from
# 1991, and SENTENÇA from 2007 — years before the old start_year=2010 default
# silently never crawled. --desde-ano lets a full backfill start earlier
# without changing the default (incremental/scheduled runs stay cheap).


def _crawl_bounds(
    ano: int | None, mes: str | None, desde_ano: int | None, now: datetime
) -> tuple[int, str | None, str | None]:
    """Resolve (start_year, end_year_month, start_year_month) for the crawl."""
    exclusive = [v is not None for v in (ano, mes, desde_ano)]
    if sum(exclusive) > 1:
        msg = "--ano, --mes and --desde-ano are mutually exclusive"
        raise typer.BadParameter(msg)
    if mes is not None:
        if not _MES_RE.fullmatch(mes):
            msg = f"--mes must be AAAA-MM, got {mes!r}"
            raise typer.BadParameter(msg)
        return int(mes[:4]), mes, mes
    if ano is not None:
        end = f"{ano:04d}-12" if ano < now.year else now.strftime("%Y-%m")
        return ano, end, None
    if desde_ano is not None:
        return desde_ano, None, None
    return _DEFAULT_START_YEAR, None, None


def _parquet_path(data_dir: Path, tipo: str, year_month: str) -> Path:
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
        "id_processo": src.get("id_processo"),
        "cd_assunto_trf": src.get("cd_assunto_trf") or "",
        "ds_assunto_trf": src.get("ds_assunto_trf") or "",
        "cd_classe_judicial": src.get("cd_classe_judicial") or "",
        "nivel_sigilo_processo": src.get("nivel_sigilo_processo"),
        "grau_jurisdicao": src.get("grau_jurisdicao"),
        "ds_md5_documento": src.get("ds_md5_documento") or "",
        "id_orgao_julgador": src.get("id_orgao_julgador"),
        "id_orgao_julgador_colegiado": src.get("id_orgao_julgador_colegiado"),
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
            if field.name in _INT_FIELD_NAMES:
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


@app.command()
def crawl(
    data_dir: Annotated[Path, typer.Argument(help="Directory to store parquet files")],
    tipo: Annotated[
        list[str] | None, typer.Option("--tipo", "-t", help="Filter to these tipos")
    ] = None,
    ano: Annotated[int | None, typer.Option("--ano", "-a", help="Only crawl this year")] = None,
    mes: Annotated[
        str | None,
        typer.Option(
            "--mes",
            "-m",
            help="Only crawl this month (AAAA-MM) — incremental mode for scheduled runs",
        ),
    ] = None,
    desde_ano: Annotated[
        int | None,
        typer.Option(
            "--desde-ano",
            help=(
                f"Full backfill starting from this year instead of the default "
                f"({_DEFAULT_START_YEAR}). Mutually exclusive with --ano/--mes."
            ),
        ),
    ] = None,
) -> None:
    """Crawl JURIS and save as parquet files per (tipo, mes_ano).

    Windows already uploaded to IA (per the manifest, restored from IA when
    no local copy exists) are skipped, except the current month, which is
    always re-crawled to pick up newly published documents.
    """
    manifest = _load_manifest(data_dir)
    tipos_to_crawl = tipo or TIPOS

    now = datetime.now(UTC)
    current_ym = now.strftime("%Y-%m")
    start_year, end_year_month, start_year_month = _crawl_bounds(ano, mes, desde_ano, now)

    def _skip(tipo_name: str, year_month: str) -> bool:
        return _should_skip_window(manifest, current_ym, tipo_name, year_month)

    for tipo_name, year_month, docs in crawl_all(
        start_year=start_year,
        end_year_month=end_year_month,
        tipos=tipos_to_crawl,
        start_year_month=start_year_month,
        skip=_skip,
    ):
        if not docs:
            continue

        rows = [_to_row(d) for d in docs]
        out = _parquet_path(data_dir, tipo_name, year_month)
        _rows_to_parquet(rows, out)
        log.info("parquet_saved", path=str(out), rows=len(rows))

        entry = ManifestJurisEntry(
            tipo=tipo_name,
            mes_ano=year_month,
            ia_status="",
            n_docs=len(docs),
        )
        manifest.upsert(entry)

    manifest.save_local(_manifest_path(data_dir))
    log.info("crawl_done")


_UPLOAD_INTERVAL_S = 1.0
# IA's S3-compatible endpoint 503s ("Slow Down") under sustained upload
# volume even WITH per-file retry/backoff (see tjro_juris.archive) — observed
# live during the historical backfill, where a whole year's worth of
# monthly parquets landed back-to-back with zero delay between PUTs. A
# small self-imposed pause between uploads mirrors the crawler's own
# _REQUEST_INTERVAL rate-limiting and cuts how often the retry path is
# needed at all, instead of just reacting to it after the fact.


@app.command()
def upload(
    data_dir: Annotated[Path, typer.Argument(help="Directory with parquet files")],
) -> None:
    """Upload parquets (and the manifest) to Internet Archive."""
    manifest = _load_manifest(data_dir)
    pending = manifest.pending_upload()

    async def _upload_all() -> None:
        for i, entry in enumerate(pending):
            if i > 0:
                await asyncio.sleep(_UPLOAD_INTERVAL_S)
            pq_path = _parquet_path(data_dir, entry.tipo, entry.mes_ano)
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

    asyncio.run(_upload_all())
    manifest.save_local(_manifest_path(data_dir))
    try:
        asyncio.run(ia_archive.upload_manifest(_manifest_path(data_dir)))
    except (httpx.HTTPError, RuntimeError) as exc:
        # Non-fatal: parquets are already on IA; the next run just re-uploads.
        log.warning("manifest_upload_failed", error=str(exc))
    log.info("upload_done", pending=len(pending))


@app.command()
def status(
    data_dir: Annotated[Path, typer.Argument(help="Directory with manifest")],
) -> None:
    """Show manifest status."""
    manifest = ManifestJuris.load_local(_manifest_path(data_dir))
    entries = manifest.all_entries()
    uploaded = sum(1 for e in entries if e.ia_status == "uploaded")
    total = len(entries)
    typer.echo(f"Total entries: {total}")
    typer.echo(f"Uploaded:      {uploaded}")
    typer.echo(f"Pending:       {total - uploaded}")


@app.command()
def consolidate(
    data_dir: Annotated[Path, typer.Argument(help="Directory with parquet files")],
    year: Annotated[int, typer.Argument(help="Year to consolidate")],
) -> None:
    """Consolidate monthly parquets for a year into a single deduplicated file."""
    parquet_files: list[Path] = []
    for tipo_name in TIPOS:
        safe_tipo = tipo_name.replace(" ", "_").replace("/", "_")
        tipo_dir = data_dir / str(year) / safe_tipo
        if tipo_dir.exists():
            parquet_files.extend(sorted(tipo_dir.glob("*.parquet")))

    output = data_dir / str(year) / f"tjro-juris-{year}.parquet"
    count = consolidate_year(parquet_files, output)
    typer.echo(f"Consolidated {count} documents to {output}")


if __name__ == "__main__":
    app()
